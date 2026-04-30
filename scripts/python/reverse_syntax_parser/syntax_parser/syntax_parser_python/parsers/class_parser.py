#!/usr/bin/env python3
import ast
import uuid

from ..constants import UUID_SEPARATOR
from .method_parser import MethodParser


class ClassParser:
    def __init__(self):
        self.method_parser = MethodParser()

    def extract_docstring(self, node):
        if node.body and isinstance(node.body[0], ast.Expr):
            v = node.body[0].value
            if isinstance(v, ast.Str):
                return v.s
            if isinstance(v, ast.Constant) and isinstance(v.value, str):
                return v.value
        return ""

    def extract_decorators(self, node):
        return [self._parse_decorator(d) for d in node.decorator_list if self._parse_decorator(d)]

    def _parse_decorator(self, decorator):
        if isinstance(decorator, ast.Name):
            return decorator.id
        elif isinstance(decorator, ast.Call):
            if isinstance(decorator.func, ast.Name):
                return decorator.func.id
            elif isinstance(decorator.func, ast.Attribute):
                return self._get_attribute_chain(decorator.func)
        elif isinstance(decorator, ast.Attribute):
            return self._get_attribute_chain(decorator)
        return None

    def _get_attribute_chain(self, node):
        parts = []
        current = node
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        return ".".join(reversed(parts)) if parts else None

    def extract_base_classes(self, node):
        bases = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                bases.append(base.id)
            elif isinstance(base, ast.Attribute):
                bases.append(f"{base.value.id}.{base.attr}")
        return bases

    def _determine_access_modifier(self, field_name):
        if field_name.startswith("__") and field_name.endswith("__"):
            return "special"
        elif field_name.startswith("__"):
            return "private"
        elif field_name.startswith("_"):
            return "protected"
        return "public"

    def parse_class_variables(self, node):
        class_vars = []
        for item in node.body:
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        class_vars.append({
                            "name": target.id,
                            "type": "class_variable",
                            "datatype": "",
                            "value": self._get_assignment_value(item.value),
                            "access_modifier": self._determine_access_modifier(target.id),
                            "lineno": item.lineno,
                        })
            elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                class_vars.append({
                    "name": item.target.id,
                    "type": "class_variable",
                    "datatype": self._get_annotation(item.annotation),
                    "value": self._get_assignment_value(item.value) if item.value else None,
                    "access_modifier": self._determine_access_modifier(item.target.id),
                    "lineno": item.lineno,
                })
        return class_vars

    def parse_methods(self, node, source_code, filename):
        methods = {}
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                method_key, method_info = self.method_parser.parse_method(
                    item, source_code, node.name, filename
                )
                methods[method_key] = method_info
        return methods

    def parse_instance_variables(self, node, source_code):
        instance_vars = []
        for item in node.body:
            if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                for stmt in item.body:
                    if isinstance(stmt, ast.Assign):
                        for target in stmt.targets:
                            if (
                                isinstance(target, ast.Attribute)
                                and isinstance(target.value, ast.Name)
                                and target.value.id == "self"
                            ):
                                instance_vars.append({
                                    "name": target.attr,
                                    "type": "instance_variable",
                                    "datatype": "",
                                    "value": self._get_assignment_value(stmt.value),
                                    "access_modifier": self._determine_access_modifier(target.attr),
                                    "lineno": stmt.lineno,
                                })
        return instance_vars

    def parse_field_list(self, node, source_code):
        class_vars = self.parse_class_variables(node)
        instance_vars = self.parse_instance_variables(node, source_code)
        all_fields = class_vars + instance_vars
        all_fields.sort(key=lambda x: x["lineno"])
        return all_fields

    def _get_annotation(self, annotation):
        if annotation is None:
            return ""
        if isinstance(annotation, ast.Name):
            return annotation.id
        elif isinstance(annotation, ast.Constant):
            return str(annotation.value)
        elif isinstance(annotation, ast.Subscript):
            if isinstance(annotation.value, ast.Name):
                return f"{annotation.value.id}[...]"
        elif isinstance(annotation, ast.Attribute):
            return f"{annotation.value.id}.{annotation.attr}"
        return str(annotation)

    def _get_assignment_value(self, value_node):
        if value_node is None:
            return None
        if isinstance(value_node, ast.Constant):
            return value_node.value
        elif isinstance(value_node, ast.Name):
            return value_node.id
        elif isinstance(value_node, (ast.List, ast.Dict)):
            return "..."
        elif isinstance(value_node, ast.Str):
            return value_node.s
        elif isinstance(value_node, ast.Num):
            return value_node.n
        return "..."

    def get_class_content(self, node, source_code):
        lines = source_code.split("\n")
        start_line = node.lineno - 1
        end_line = node.end_lineno if hasattr(node, "end_lineno") else start_line + 1
        return "\n".join(lines[start_line:end_line])

    def parse_class(self, node, source_code, filename):
        unique_id = str(uuid.uuid4())
        class_key = f"{node.name}{UUID_SEPARATOR}{unique_id}"
        class_info = {
            "type": "class_definition",
            "content": self.get_class_content(node, source_code),
            "filename": filename,
            "name": node.name,
            "uuid": unique_id,
            "base_classes": self.extract_base_classes(node),
            "docstring": self.extract_docstring(node),
            "decorators": self.extract_decorators(node),
            "dependencies": self.extract_class_dependencies(node),
            "methods": self.parse_methods(node, source_code, filename),
            "field_list": self.parse_field_list(node, source_code),
            "lineno": node.lineno,
            "end_lineno": getattr(node, "end_lineno", node.lineno),
        }
        return class_key, class_info

    def extract_class_dependencies(self, node):
        deps = set()
        for base in node.bases:
            if isinstance(base, ast.Name):
                deps.add(base.id)
            elif isinstance(base, ast.Attribute):
                deps.add(f"{base.value.id}.{base.attr}")
        for child in ast.walk(node):
            if isinstance(child, ast.Call) and self._is_class_level_call(child, node):
                cn = self._extract_call_name(child)
                if cn:
                    deps.add(cn)
        return list(deps)

    def _is_class_level_call(self, call_node, class_node):
        for child in class_node.body:
            if isinstance(child, ast.Assign):
                for n in ast.walk(child):
                    if n == call_node:
                        return True
            elif child == call_node:
                return True
        return False

    def _extract_call_name(self, call_node):
        if isinstance(call_node.func, ast.Name):
            return call_node.func.id
        elif isinstance(call_node.func, ast.Attribute):
            if isinstance(call_node.func.value, ast.Name):
                return f"{call_node.func.value.id}.{call_node.func.attr}"
            return call_node.func.attr
        return None
