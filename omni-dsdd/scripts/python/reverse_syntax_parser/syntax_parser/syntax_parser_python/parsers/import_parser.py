#!/usr/bin/env python3
import ast
import uuid

from ..constants import UUID_SEPARATOR


class ImportParser:
    def parse_import(self, node, source_code, filename):
        unique_id = str(uuid.uuid4())
        import_info = {
            "type": "import_statement",
            "content": self.get_import_content(node, source_code),
            "filename": filename,
            "uuid": unique_id,
            "lineno": node.lineno,
        }
        if isinstance(node, ast.Import):
            modules = [a.name for a in node.names]
            aliases = [a.asname or a.name for a in node.names]
            import_info.update({"import_type": "import", "modules": modules, "aliases": aliases})
            import_key = f"import_{modules[0].replace('.', '_')}{UUID_SEPARATOR}{unique_id}"
        else:
            module = node.module or ""
            names = [a.name for a in node.names]
            aliases = [a.asname or a.name for a in node.names]
            import_info.update({
                "import_type": "from_import",
                "module": module,
                "names": names,
                "aliases": aliases,
                "level": node.level,
            })
            if module:
                import_key = f"from_{module.replace('.', '_')}_import_{names[0] if names else 'all'}{UUID_SEPARATOR}{unique_id}"
            else:
                import_key = f"from_relative_import_{names[0] if names else 'all'}{UUID_SEPARATOR}{unique_id}"
        return import_key, import_info

    def get_import_content(self, node, source_code):
        lines = source_code.split("\n")
        idx = node.lineno - 1
        return lines[idx].strip() if idx < len(lines) else ""
