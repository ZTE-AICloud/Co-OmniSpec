#!/usr/bin/env python3
import ast
import uuid

from ..constants import UUID_SEPARATOR


class VariableParser:
    def parse_assignment(self, node, source_code, filename):
        assignments = []
        names = []
        for target in node.targets:
            if isinstance(target, ast.Name):
                unique_id = str(uuid.uuid4())
                var_key = f"{target.id}{UUID_SEPARATOR}{unique_id}"
                var_info = {
                    "type": "global_variable",
                    "content": self.get_assignment_content(node, source_code),
                    "filename": filename,
                    "name": target.id,
                    "uuid": unique_id,
                    "value": self._get_assignment_value(node.value),
                    "datatype": self._infer_type(node.value),
                    "lineno": node.lineno,
                }
                assignments.append(var_info)
                names.append(var_key)
            elif isinstance(target, ast.Tuple):
                for i, elt in enumerate(target.elts):
                    if isinstance(elt, ast.Name):
                        unique_id = str(uuid.uuid4())
                        var_key = f"{elt.id}{UUID_SEPARATOR}{unique_id}"
                        var_info = {
                            "type": "global_variable",
                            "content": self.get_assignment_content(node, source_code),
                            "filename": filename,
                            "name": elt.id,
                            "uuid": unique_id,
                            "value": f"unpacked_value_{i}",
                            "datatype": "unknown",
                            "lineno": node.lineno,
                        }
                        assignments.append(var_info)
                        names.append(var_key)
        return names, assignments

    def parse_constant_assignment(self, node, source_code, filename):
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
        ):
            var_name = node.targets[0].id
            is_constant = (
                var_name.isupper()
                or (var_name.startswith("_") and var_name[1:].replace("_", "").isupper())
                or any(
                    kw in var_name.upper()
                    for kw in ["DEFAULT", "MAX", "MIN", "CONFIG", "VERSION", "CONSTANT", "API_"]
                )
            )
            if is_constant:
                unique_id = str(uuid.uuid4())
                var_key = f"{var_name}{UUID_SEPARATOR}{unique_id}"
                var_info = {
                    "type": "constant_definition",
                    "content": self.get_assignment_content(node, source_code),
                    "filename": filename,
                    "name": var_name,
                    "uuid": unique_id,
                    "value": self._get_assignment_value(node.value),
                    "datatype": self._infer_type(node.value),
                    "lineno": node.lineno,
                }
                return var_key, var_info
        return None, None

    def _get_assignment_value(self, value_node):
        if value_node is None:
            return None
        if isinstance(value_node, ast.Constant):
            v = value_node.value
            if isinstance(v, bytes):
                return f"b'{v[:50].decode('utf-8', errors='ignore')}...'"
            return v
        elif isinstance(value_node, ast.Name):
            return value_node.id
        elif isinstance(value_node, ast.List):
            return [...]
        elif isinstance(value_node, ast.Dict):
            return {}
        elif isinstance(value_node, ast.Call):
            if isinstance(value_node.func, ast.Name):
                return f"{value_node.func.id}(...)"
            return "function_call(...)"
        return "..."

    def _infer_type(self, value_node):
        if value_node is None:
            return "None"
        if isinstance(value_node, ast.Constant):
            return type(value_node.value).__name__
        elif isinstance(value_node, ast.List):
            return "list"
        elif isinstance(value_node, ast.Dict):
            return "dict"
        elif isinstance(value_node, ast.Set):
            return "set"
        elif isinstance(value_node, ast.Tuple):
            return "tuple"
        elif isinstance(value_node, ast.Name):
            return "variable_reference"
        return "unknown"

    def get_assignment_content(self, node, source_code):
        lines = source_code.split("\n")
        idx = node.lineno - 1
        return lines[idx].strip() if idx < len(lines) else ""
