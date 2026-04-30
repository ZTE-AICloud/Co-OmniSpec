#!/usr/bin/env python3
import os
import ast

from ..constants import UUID_SEPARATOR
from .function_parser import FunctionParser
from .class_parser import ClassParser
from .variable_parser import VariableParser
from .import_parser import ImportParser


class PythonParser:
    def __init__(self):
        self.elements = {}
        self.python_files = []
        self.project_directory = None
        self.name_to_uuid_map = {}
        self.classified_elements = {}
        self.function_parser = FunctionParser()
        self.class_parser = ClassParser()
        self.variable_parser = VariableParser()
        self.import_parser = ImportParser()

    def find_files(self, directory):
        for root, dirs, files in os.walk(directory):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d != "__pycache__"]
            for f in files:
                if not f.startswith(".") and f.endswith(".py"):
                    self.python_files.append(os.path.join(root, f))

    def process_file(self, filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                source_code = f.read()
        except UnicodeDecodeError:
            try:
                with open(filepath, "r", encoding="gbk") as f:
                    source_code = f.read()
            except Exception:
                return
        filename = (
            os.path.relpath(filepath, self.project_directory).replace("\\", "/")
            if self.project_directory
            else os.path.basename(filepath)
        )
        try:
            tree = ast.parse(source_code)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    if not self._is_method(node, tree):
                        uuid_key, info = self.function_parser.parse_function(
                            node, source_code, filename
                        )
                        if uuid_key:
                            self.elements[uuid_key] = info
                            self._add_to_map(info.get("name"), uuid_key)
                elif isinstance(node, ast.AsyncFunctionDef):
                    if not self._is_method(node, tree):
                        uuid_key, info = self.function_parser.parse_async_function(
                            node, source_code, filename
                        )
                        if uuid_key:
                            self.elements[uuid_key] = info
                            self._add_to_map(info.get("name"), uuid_key)
                elif isinstance(node, ast.ClassDef):
                    uuid_key, info = self.class_parser.parse_class(
                        node, source_code, filename
                    )
                    if uuid_key:
                        self.elements[uuid_key] = info
                        self._add_to_map(info.get("name"), uuid_key)
                        for mk, mi in info.get("methods", {}).items():
                            self._add_to_map(mi.get("name"), mk)
                elif isinstance(node, ast.Assign):
                    if self._is_global_assignment(node, tree):
                        const_key, const_info = self.variable_parser.parse_constant_assignment(
                            node, source_code, filename
                        )
                        if const_key:
                            self.elements[const_key] = const_info
                            self._add_to_map(const_info.get("name"), const_key)
                        else:
                            names, infos = self.variable_parser.parse_assignment(
                                node, source_code, filename
                            )
                            for n, i in zip(names, infos):
                                if n:
                                    self.elements[n] = i
                                    self._add_to_map(i.get("name"), n)
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    uuid_key, info = self.import_parser.parse_import(
                        node, source_code, filename
                    )
                    if uuid_key:
                        self.elements[uuid_key] = info
        except (SyntaxError, Exception):
            pass

    def _add_to_map(self, name, uuid_key):
        if name:
            if name not in self.name_to_uuid_map:
                self.name_to_uuid_map[name] = []
            self.name_to_uuid_map[name].append(uuid_key)

    def _is_method(self, func_node, tree):
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for child in node.body:
                    if child == func_node:
                        return True
        return False

    def _is_global_assignment(self, assign_node, tree):
        for node in tree.body:
            if node == assign_node:
                return True
        return False

    def parse_project(self, project_path):
        self.project_directory = project_path
        self.find_files(project_path)
        for fp in self.python_files:
            self.process_file(fp)
        self._update_dependencies_with_uuids()
        return self.elements

    def _update_dependencies_with_uuids(self):
        for elem_key, elem_info in self.elements.items():
            if "dependencies" in elem_info and elem_info["dependencies"]:
                elem_info["dependencies"] = self._convert_dependencies_to_uuid(
                    elem_info["dependencies"]
                )
            if elem_info.get("type") == "class_definition":
                for mk, mi in elem_info.get("methods", {}).items():
                    if "dependencies" in mi and mi["dependencies"]:
                        mi["dependencies"] = self._convert_dependencies_to_uuid(
                            mi["dependencies"]
                        )

    def _convert_dependencies_to_uuid(self, dependencies):
        updated = []
        for dep in dependencies:
            if UUID_SEPARATOR in dep:
                if self._is_valid_uuid_key(dep):
                    updated.append(dep)
                continue
            resolved = self._resolve_dependency_to_uuid(dep)
            if resolved is not None:
                updated.append(resolved)
        return updated

    def _is_valid_uuid_key(self, uuid_key):
        for elements_dict in self.classified_elements.values():
            if uuid_key in elements_dict:
                return True
        return False

    def _resolve_dependency_to_uuid(self, dep_name):
        if dep_name in self.name_to_uuid_map:
            return self.name_to_uuid_map[dep_name][0]
        if dep_name.startswith("self."):
            mn = dep_name[5:]
            if mn in self.name_to_uuid_map:
                for uk in self.name_to_uuid_map[mn]:
                    ei = self._get_element_by_uuid_key(uk)
                    if ei and ei.get("type") == "method_definition":
                        return uk
                return self.name_to_uuid_map[mn][0]
        if dep_name.startswith("super()."):
            mn = dep_name[8:]
            if mn in self.name_to_uuid_map:
                for uk in self.name_to_uuid_map[mn]:
                    ei = self._get_element_by_uuid_key(uk)
                    if ei and ei.get("type") == "method_definition":
                        return uk
                return self.name_to_uuid_map[mn][0]
        if "." in dep_name:
            parts = dep_name.split(".")
            if len(parts) == 2:
                cn, mn = parts
                if cn in self.name_to_uuid_map and mn in self.name_to_uuid_map:
                    for uk in self.name_to_uuid_map[mn]:
                        ei = self._get_element_by_uuid_key(uk)
                        if ei and ei.get("type") == "method_definition":
                            ck = ei.get("class_key", "")
                            if ck.startswith(f"{cn}{UUID_SEPARATOR}"):
                                return uk
                    if cn in self.name_to_uuid_map:
                        return self.name_to_uuid_map[cn][0]
        return None

    def _get_element_by_uuid_key(self, uuid_key):
        for elements_dict in self.classified_elements.values():
            if uuid_key in elements_dict:
                return elements_dict[uuid_key]
        return None

    def _rebuild_name_to_uuid_map_after_split(self, classified_elements):
        self.name_to_uuid_map = {}
        self.classified_elements = classified_elements
        for elements_dict in classified_elements.values():
            for uuid_key, elem_info in elements_dict.items():
                name = elem_info.get("name")
                if name:
                    if name not in self.name_to_uuid_map:
                        self.name_to_uuid_map[name] = []
                    self.name_to_uuid_map[name].append(uuid_key)

    def _update_dependencies_after_split(self, classified_elements):
        for elements_dict in classified_elements.values():
            for uuid_key, elem_info in elements_dict.items():
                if "dependencies" in elem_info and elem_info["dependencies"]:
                    elem_info["dependencies"] = self._convert_dependencies_to_uuid(
                        elem_info["dependencies"]
                    )
