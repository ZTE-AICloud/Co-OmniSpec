#!/usr/bin/env python3
import ast
import re
import uuid

from ..constants import UUID_SEPARATOR


class FunctionParser:
    def extract_function_calls(self, node):
        function_calls = set()
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                call_name = self._extract_call_name(child)
                if call_name:
                    function_calls.add(call_name)
                class_name = self._extract_class_name_from_call(child)
                if class_name:
                    function_calls.add(class_name)
        return list(function_calls)

    def _extract_call_name(self, call_node):
        if isinstance(call_node.func, ast.Name):
            return call_node.func.id
        elif isinstance(call_node.func, ast.Attribute):
            if isinstance(call_node.func.value, ast.Name):
                return f"{call_node.func.value.id}.{call_node.func.attr}"
            return call_node.func.attr
        elif isinstance(call_node.func, ast.Subscript):
            if isinstance(call_node.func.value, ast.Name):
                return call_node.func.value.id
        return None

    def _extract_class_name_from_call(self, call_node):
        if isinstance(call_node.func, ast.Attribute):
            if isinstance(call_node.func.value, ast.Name):
                cn = call_node.func.value.id
                if cn and cn[0].isupper():
                    return cn
        return None

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
        try:
            if isinstance(decorator, ast.Name):
                return decorator.id
            elif isinstance(decorator, ast.Attribute):
                return self._get_attribute_chain(decorator)
            elif isinstance(decorator, ast.Call):
                return self._get_call_function_name(decorator)
        except Exception:
            pass
        return None

    def _get_attribute_chain(self, node):
        parts = []
        current = node
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        return ".".join(reversed(parts))

    def _get_call_function_name(self, call_node):
        if isinstance(call_node.func, ast.Name):
            return call_node.func.id
        elif isinstance(call_node.func, ast.Attribute):
            return self._get_attribute_chain(call_node.func)
        return None

    def parse_parameters(self, node):
        params = []
        args = node.args
        for i, arg in enumerate(args.args):
            param_info = {
                "name": arg.arg,
                "datatype": self._get_annotation(arg.annotation) if arg.annotation else "",
                "default": None,
            }
            defaults_offset = len(args.args) - len(args.defaults)
            if i >= defaults_offset:
                param_info["default"] = self._get_default_value(args.defaults[i - defaults_offset])
            params.append(param_info)
        if args.vararg:
            params.append({"name": f"*{args.vararg.arg}", "datatype": "", "default": None})
        if args.kwarg:
            params.append({"name": f"**{args.kwarg.arg}", "datatype": "", "default": None})
        return params

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

    def _get_default_value(self, default_node):
        if isinstance(default_node, ast.Constant):
            return default_node.value
        elif isinstance(default_node, ast.Name):
            return default_node.id
        elif isinstance(default_node, (ast.List, ast.Dict)):
            return "..."
        return "..."

    def get_function_content(self, node, source_code):
        lines = source_code.split("\n")
        start_line = node.lineno - 1
        end_line = node.end_lineno if hasattr(node, "end_lineno") else start_line + 1
        return "\n".join(lines[start_line:end_line])

    def parse_function(self, node, source_code, filename):
        unique_id = str(uuid.uuid4())
        function_key = f"{node.name}{UUID_SEPARATOR}{unique_id}"
        function_info = {
            "type": "function_definition",
            "content": self.get_function_content(node, source_code),
            "filename": filename,
            "name": node.name,
            "uuid": unique_id,
            "params": self.parse_parameters(node),
            "return_type": self._get_annotation(node.returns) if node.returns else "",
            "docstring": self.extract_docstring(node),
            "decorators": self.extract_decorators(node),
            "dependencies": self.extract_function_calls(node),
            "lineno": node.lineno,
            "end_lineno": getattr(node, "end_lineno", node.lineno),
        }
        return function_key, function_info

    def parse_async_function(self, node, source_code, filename):
        unique_id = str(uuid.uuid4())
        function_key = f"{node.name}{UUID_SEPARATOR}{unique_id}"
        function_info = {
            "type": "function_definition",
            "content": self.get_function_content(node, source_code),
            "filename": filename,
            "name": node.name,
            "uuid": unique_id,
            "params": self.parse_parameters(node),
            "return_type": self._get_annotation(node.returns) if node.returns else "",
            "docstring": self.extract_docstring(node),
            "decorators": self.extract_decorators(node),
            "dependencies": self.extract_function_calls(node),
            "is_async": True,
            "lineno": node.lineno,
            "end_lineno": getattr(node, "end_lineno", node.lineno),
        }
        return function_key, function_info
