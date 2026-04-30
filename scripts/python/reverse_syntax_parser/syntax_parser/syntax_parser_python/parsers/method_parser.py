#!/usr/bin/env python3
import ast
import uuid

from ..constants import UUID_SEPARATOR


class MethodParser:
    def parse_method(self, node, source_code, class_name=None, filename=None):
        unique_id = str(uuid.uuid4())
        method_key = f"{node.name}{UUID_SEPARATOR}{unique_id}"
        method_info = {
            "name": node.name,
            "uuid": unique_id,
            "content": self.get_method_content(node, source_code),
            "elem_datatype": self._get_annotation(node.returns) if node.returns else "",
            "params": self.parse_parameters(node),
            "docstring": self.extract_docstring(node),
            "decorators": self.extract_decorators(node),
            "dependencies": self.extract_function_calls(node),
            "access_modifier": self._determine_access_modifier(node.name),
            "is_static": self._is_static_method(node),
            "is_class_method": self._is_class_method(node),
            "is_property": self._is_property(node),
            "is_async": isinstance(node, ast.AsyncFunctionDef),
            "is_abstract": self._is_abstract_method(node),
            "is_constructor": node.name == "__init__",
            "is_destructor": node.name == "__del__",
            "is_special": self._is_special_method(node.name),
            "lineno": node.lineno,
            "end_lineno": getattr(node, "end_lineno", node.lineno),
            "class_name": class_name,
            "filename": filename,
        }
        return method_key, method_info

    def parse_parameters(self, node):
        params = []
        args = node.args
        for i, arg in enumerate(args.args):
            param_info = {
                "name": arg.arg,
                "datatype": self._get_annotation(arg.annotation) if arg.annotation else "",
                "default": None,
                "is_self": arg.arg == "self" and i == 0,
                "is_cls": arg.arg == "cls" and i == 0,
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

    def extract_function_calls(self, node):
        calls = set()
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                cn = self._extract_call_name(child)
                if cn:
                    calls.add(cn)
                ccn = self._extract_class_name_from_call(child)
                if ccn:
                    calls.add(ccn)
        return list(calls)

    def _extract_call_name(self, call_node):
        if isinstance(call_node.func, ast.Name):
            return call_node.func.id
        elif isinstance(call_node.func, ast.Attribute):
            if isinstance(call_node.func.value, ast.Name):
                if call_node.func.value.id == "self":
                    return f"self.{call_node.func.attr}"
                elif call_node.func.value.id == "super":
                    return f"super().{call_node.func.attr}"
                return f"{call_node.func.value.id}.{call_node.func.attr}"
            return call_node.func.attr
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

    def _determine_access_modifier(self, method_name):
        if method_name.startswith("__") and method_name.endswith("__"):
            return "special"
        elif method_name.startswith("__"):
            return "private"
        elif method_name.startswith("_"):
            return "protected"
        return "public"

    def _is_static_method(self, node):
        return any(isinstance(d, ast.Name) and d.id == "staticmethod" for d in node.decorator_list)

    def _is_class_method(self, node):
        return any(isinstance(d, ast.Name) and d.id == "classmethod" for d in node.decorator_list)

    def _is_property(self, node):
        for d in node.decorator_list:
            if isinstance(d, ast.Name) and d.id in ("property", "cached_property"):
                return True
            if isinstance(d, ast.Attribute) and d.attr in ("setter", "getter", "deleter"):
                return True
        return False

    def _is_abstract_method(self, node):
        for d in node.decorator_list:
            if isinstance(d, ast.Name) and d.id == "abstractmethod":
                return True
            if isinstance(d, ast.Attribute) and d.attr == "abstractmethod":
                return True
        return False

    def _is_special_method(self, method_name):
        return method_name.startswith("__") and method_name.endswith("__")

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
        elif isinstance(default_node, (ast.List, ast.Dict, ast.Set, ast.Tuple)):
            return "..."
        return "..."

    def get_method_content(self, node, source_code):
        lines = source_code.split("\n")
        start_line = node.lineno - 1
        end_line = node.end_lineno if hasattr(node, "end_lineno") else start_line + 1
        return "\n".join(lines[start_line:end_line])
