#  Copyright 2008-2015 Nokia Networks
#  Copyright 2016-     Robot Framework Foundation
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import copy
import os
from collections import OrderedDict
from itertools import chain

from robot.errors import DataError, KeywordError
from robot.libraries import STDLIBS
from robot.output import LOGGER, Message
from robot.utils import (RecommendationFinder, eq, find_file, is_string, normalize,
                         plural_or_not as s, printable_name, seq2str, seq2str2)

from .context import EXECUTION_CONTEXTS
from .importer import ImportCache, Importer
from .model import Import
from .runkwregister import RUN_KW_REGISTER
from .usererrorhandler import UserErrorHandler
from .userkeyword import UserLibrary

IMPORTER = Importer()


class Namespace:
    _default_libraries = ('BuiltIn', 'Reserved', 'Easter')
    _library_import_by_path_ends = ('.py', '/', os.sep)
    _variables_import_by_path_ends = _library_import_by_path_ends + ('.yaml', '.yml')

    def __init__(self, variables, suite, resource, languages):
        LOGGER.info(f"Initializing namespace for suite '{suite.longname}'.")
        self.variables = variables
        self.languages = languages
        self._imports = resource.imports
        self._kw_store = KeywordStore(resource, languages)
        self._imported_variable_files = ImportCache()
        self._suite_name = suite.longname
        self._running_test = False

    @property
    def libraries(self):
        return self._kw_store.libraries.values()

    def handle_imports(self):
        self._import_default_libraries()
        self._handle_imports(self._imports)

    def _import_default_libraries(self):
        for name in self._default_libraries:
            self.import_library(name, notify=name == 'BuiltIn')

    def _handle_imports(self, import_settings):
        for item in import_settings:
            try:
                if not item.name:
                    raise DataError(f'{item.type} setting requires value.')
                self._import(item)
            except DataError as err:
                item.report_invalid_syntax(err.message)

    def _import(self, import_setting):
        action = {'Library': self._import_library,
                  'Resource': self._import_resource,
                  'Variables': self._import_variables}[import_setting.type]
        action(import_setting)

    def import_resource(self, name, overwrite=True):
        self._import_resource(Import('Resource', name), overwrite=overwrite)

    def _import_resource(self, import_setting, overwrite=False):
        path = self._resolve_name(import_setting)
        self._validate_not_importing_init_file(path)
        if overwrite or path not in self._kw_store.resources:
            resource = IMPORTER.import_resource(path, self.languages)
            self.variables.set_from_variable_table(resource.variables, overwrite)
            user_library = UserLibrary(resource)
            self._kw_store.resources[path] = user_library
            self._handle_imports(resource.imports)
            LOGGER.imported("Resource", user_library.name,
                            importer=import_setting.source,
                            source=path)
        else:
            LOGGER.info(f"Resource file '{path}' already imported by "
                        f"suite '{self._suite_name}'.")

    def _validate_not_importing_init_file(self, path):
        name = os.path.splitext(os.path.basename(path))[0]
        if name.lower() == '__init__':
            raise DataError(f"Initialization file '{path}' cannot be imported as "
                            f"a resource file.")

    def import_variables(self, name, args, overwrite=False):
        self._import_variables(Import('Variables', name, args), overwrite)

    def _import_variables(self, import_setting, overwrite=False):
        path = self._resolve_name(import_setting)
        args = self._resolve_args(import_setting)
        if overwrite or (path, args) not in self._imported_variable_files:
            self._imported_variable_files.add((path, args))
            self.variables.set_from_file(path, args, overwrite)
            LOGGER.imported("Variables", os.path.basename(path),
                            args=list(args),
                            importer=import_setting.source,
                            source=path)
        else:
            msg = f"Variable file '{path}'"
            if args:
                msg += f" with arguments {seq2str2(args)}"
            LOGGER.info(f"{msg} already imported by suite '{self._suite_name}'.")

    def import_library(self, name, args=(), alias=None, notify=True):
        self._import_library(Import('Library', name, args, alias),
                             notify=notify)

    def _import_library(self, import_setting, notify=True):
        name = self._resolve_name(import_setting)
        lib = IMPORTER.import_library(name, import_setting.args,
                                      import_setting.alias, self.variables)
        if lib.name in self._kw_store.libraries:
            LOGGER.info(f"Library '{lib.name}' already imported by suite "
                        f"'{self._suite_name}'.")
            return
        if notify:
            LOGGER.imported("Library", lib.name,
                            args=list(import_setting.args),
                            originalname=lib.orig_name,
                            importer=import_setting.source,
                            source=lib.source)
        self._kw_store.libraries[lib.name] = lib
        lib.start_suite()
        if self._running_test:
            lib.start_test()

    def _resolve_name(self, setting):
        name = setting.name
        try:
            name = self.variables.replace_string(name)
        except DataError as err:
            self._raise_replacing_vars_failed(setting, err)
        if self._is_import_by_path(setting.type, name):
            return find_file(name, setting.directory, file_type=setting.type)
        return name

    def _raise_replacing_vars_failed(self, setting, error):
        raise DataError(f"Replacing variables from setting '{setting.type}' "
                        f"failed: {error}")

    def _is_import_by_path(self, import_type, path):
        if import_type == 'Library':
            return path.lower().endswith(self._library_import_by_path_ends)
        if import_type == 'Variables':
            return path.lower().endswith(self._variables_import_by_path_ends)
        return True

    def _resolve_args(self, import_setting):
        try:
            return self.variables.replace_list(import_setting.args)
        except DataError as err:
            self._raise_replacing_vars_failed(import_setting, err)

    def set_search_order(self, new_order):
        old_order = self._kw_store.search_order
        self._kw_store.search_order = new_order
        return old_order

    def start_test(self):
        self._running_test = True
        self.variables.start_test()
        for lib in self.libraries:
            lib.start_test()

    def end_test(self):
        self.variables.end_test()
        for lib in self.libraries:
            lib.end_test()
        self._running_test = True

    def start_suite(self):
        self.variables.start_suite()

    def end_suite(self, suite):
        for lib in self.libraries:
            lib.end_suite()
        if not suite.parent:
            IMPORTER.close_global_library_listeners()
        self.variables.end_suite()

    def start_user_keyword(self):
        self.variables.start_keyword()

    def end_user_keyword(self):
        self.variables.end_keyword()

    def get_library_instance(self, libname):
        return self._kw_store.get_library(libname).get_instance()

    def get_library_instances(self):
        return dict((name, lib.get_instance())
                    for name, lib in self._kw_store.libraries.items())

    def reload_library(self, libname_or_instance):
        library = self._kw_store.get_library(libname_or_instance)
        library.reload()
        return library

    def get_runner(self, name):
        try:
            return self._kw_store.get_runner(name)
        except DataError as error:
            return UserErrorHandler(error, name)


class KeywordStore:

    def __init__(self, resource, languages):
        self.user_keywords = UserLibrary(resource, UserLibrary.TEST_CASE_FILE_TYPE)
        self.libraries = OrderedDict()
        self.resources = ImportCache()
        self.search_order = ()
        self.languages = languages

    def get_library(self, name_or_instance):
        if name_or_instance is None:
            raise DataError("Library can not be None.")
        if is_string(name_or_instance):
            return self._get_lib_by_name(name_or_instance)
        return self._get_lib_by_instance(name_or_instance)

    def _get_lib_by_name(self, name):
        if name in self.libraries:
            return self.libraries[name]
        matches = [lib for lib in self.libraries.values() if eq(lib.name, name)]
        if len(matches) == 1:
            return matches[0]
        self._no_library_found(name, multiple=bool(matches))

    def _no_library_found(self, name, multiple=False):
        if multiple:
            raise DataError(f"Multiple libraries matching '{name}' found.")
        raise DataError(f"No library '{name}' found.")

    def _get_lib_by_instance(self, instance):
        for lib in self.libraries.values():
            if lib.get_instance(create=False) is instance:
                return lib
        self._no_library_found(instance)

    def get_runner(self, name):
        runner = self._get_runner(name)
        if runner is None:
            self._raise_no_keyword_found(name)
        return runner

    def _raise_no_keyword_found(self, name):
        if name.strip(': ').upper() == 'FOR':
            raise KeywordError(
                f"Support for the old FOR loop syntax has been removed. "
                f"Replace '{name}' with 'FOR', end the loop with 'END', and "
                f"remove escaping backslashes."
            )
        if name == '\\':
            raise KeywordError(
                "No keyword with name '\\' found. If it is used inside a for "
                "loop, remove escaping backslashes and end the loop with 'END'."
            )
        message = f"No keyword with name '{name}' found."
        finder = KeywordRecommendationFinder(self.user_keywords,
                                             self.libraries,
                                             self.resources)
        raise KeywordError(finder.recommend_similar_keywords(name, message))

    def _get_runner(self, name):
        if not name:
            raise DataError('Keyword name cannot be empty.')
        if not is_string(name):
            raise DataError('Keyword name must be a string.')
        runner = self._get_runner_from_test_case_file(name)
        if not runner and '.' in name:
            runner = self._get_explicit_runner(name)
        if not runner:
            runner = self._get_implicit_runner(name)
        if not runner:
            runner = self._get_bdd_style_runner(name)
        return runner

    def _get_bdd_style_runner(self, name):
        parts = name.split(maxsplit=1)
        if len(parts) < 2:
            return None
        prefix, keyword = parts
        if prefix.title() in self.languages.bdd_prefixes:
            runner = self._get_runner(keyword)
            if runner:
                runner = copy.copy(runner)
                runner.name = name
                return runner
        return None

    def _get_implicit_runner(self, name):
        runner = self._get_runner_from_resource_files(name)
        if not runner:
            runner = self._get_runner_from_libraries(name)
        return runner

    def _get_runner_from_test_case_file(self, name):
        if name in self.user_keywords.handlers:
            return self.user_keywords.handlers.create_runner(name)

    def _get_runner_from_resource_files(self, name):
        found = [lib.handlers.create_runner(name)
                 for lib in self.resources.values()
                 if name in lib.handlers]
        if not found:
            return None
        if len(found) > 1:
            found = self._get_runner_based_on_search_order(found)
        if len(found) > 1:
            found = self._get_runner_from_same_resource_file(found)
        if len(found) > 1:
            found = self._handle_private_user_keywords(found)
        if len(found) == 1:
            return found[0]
        self._raise_multiple_keywords_found(found, name)

    def _get_runner_from_libraries(self, name):
        found = [lib.handlers.create_runner(name) for lib in self.libraries.values()
                 if name in lib.handlers]
        if not found:
            return None
        if len(found) > 1:
            found = self._get_runner_based_on_search_order(found)
        if len(found) == 2:
            found = self._filter_stdlib_runner(*found)
        if len(found) == 1:
            return found[0]
        self._raise_multiple_keywords_found(found, name)

    def _get_runner_from_same_resource_file(self, found):
        user_keywords = EXECUTION_CONTEXTS.current.user_keywords
        if not user_keywords:
            return found
        parent_source = user_keywords[-1].source
        for runner in found:
            if runner.source == parent_source:
                return [runner]
        return found

    def _handle_private_user_keywords(self, runners):
        public = [r for r in runners if not r.private]
        return public if len(public) == 1 else runners

    def _get_runner_based_on_search_order(self, runners):
        for libname in self.search_order:
            for runner in runners:
                if eq(libname, runner.libname):
                    return [runner]
        return runners

    def _filter_stdlib_runner(self, runner1, runner2):
        stdlibs_without_remote = STDLIBS - {'Remote'}
        if runner1.library.orig_name in stdlibs_without_remote:
            standard, custom = runner1, runner2
        elif runner2.library.orig_name in stdlibs_without_remote:
            standard, custom = runner2, runner1
        else:
            return [runner1, runner2]
        if not RUN_KW_REGISTER.is_run_keyword(custom.library.orig_name, custom.name):
            self._custom_and_standard_keyword_conflict_warning(custom, standard)
        return [custom]

    def _custom_and_standard_keyword_conflict_warning(self, custom, standard):
        custom_with_name = standard_with_name = ''
        if custom.library.name != custom.library.orig_name:
            custom_with_name = f" imported as '{custom.library.name}'"
        if standard.library.name != standard.library.orig_name:
            standard_with_name = f" imported as '{standard.library.name}'"
        warning = Message(
            f"Keyword '{standard.name}' found both from a custom library "
            f"'{custom.library.orig_name}'{custom_with_name} and a standard library "
            f"'{standard.library.orig_name}'{standard_with_name}. The custom keyword "
            f"is used. To select explicitly, and to get rid of this warning, use "
            f"either '{custom.longname}' or '{standard.longname}'.",
            level='WARN'
        )
        if custom.pre_run_messages:
            custom.pre_run_messages.append(warning)
        else:
            custom.pre_run_messages = [warning]

    def _get_explicit_runner(self, name):
        found = []
        for owner_name, kw_name in self._yield_owner_and_kw_names(name):
            found.extend(self._find_keywords(owner_name, kw_name))
        if len(found) > 1:
            self._raise_multiple_keywords_found(found, name, implicit=False)
        return found[0] if found else None

    def _yield_owner_and_kw_names(self, full_name):
        tokens = full_name.split('.')
        for i in range(1, len(tokens)):
            yield '.'.join(tokens[:i]), '.'.join(tokens[i:])

    def _find_keywords(self, owner_name, name):
        return [owner.handlers.create_runner(name)
                for owner in chain(self.libraries.values(), self.resources.values())
                if eq(owner.name, owner_name) and name in owner.handlers]

    def _raise_multiple_keywords_found(self, runners, used_as, implicit=True):
        error = f"Multiple keywords with name '{used_as}' found"
        if implicit:
            error += ". Give the full name of the keyword you want to use"
        names = sorted(r.longname for r in runners)
        raise KeywordError('\n    '.join([error+':'] + names))


class KeywordRecommendationFinder:

    def __init__(self, user_keywords, libraries, resources):
        self.user_keywords = user_keywords
        self.libraries = libraries
        self.resources = resources

    def recommend_similar_keywords(self, name, message):
        """Return keyword names similar to `name`."""
        candidates = self._get_candidates('.' in name)
        finder = RecommendationFinder(
            lambda name: normalize(candidates.get(name, name), ignore='_')
        )
        return finder.find_and_format(name, candidates, message,
                                      check_missing_argument_separator=True)

    @staticmethod
    def format_recommendations(message, recommendations):
        return RecommendationFinder().format(message, recommendations)

    def _get_candidates(self, use_full_name):
        names = {}
        for owner, name in self._get_all_handler_names():
            full_name = f'{owner}.{name}' if owner else name
            names[full_name] = full_name if use_full_name else name
        return names

    def _get_all_handler_names(self):
        """Return a list of `(library_name, handler_name)` tuples."""
        handlers = [('', printable_name(handler.name, True))
                    for handler in self.user_keywords.handlers]
        for library in chain(self.libraries.values(), self.resources.values()):
            if library.name != 'Reserved':
                handlers.extend(
                    ((library.name or '',
                      printable_name(handler.name, code_style=True))
                     for handler in library.handlers))
        return sorted(handlers)
