#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
代码库语言类型识别工具
输入：代码库路径
输出：检测到的编程语言类型（字符串）
"""

import json
import argparse
import sys
from pathlib import Path
from collections import Counter
from typing import Dict, List, Any

from utils import get_logger


class CodeLanguageDetector:
    """代码库语言类型检测器"""

    def __init__(self):
        self.logger = get_logger("get_code_type")
        self.language_extensions = {
            "python": [".py", ".pyw", ".pyi", ".pyx"],
            "java": [".java", ".jav"],
            "cpp": [".cpp", ".cxx", ".cc", ".c++", ".hpp", ".hxx", ".hh", ".h++", ".h"],
            "c": [".c", ".h"],
            "javascript": [".js", ".jsx", ".ts", ".tsx", ".mjs"],
            "go": [".go"],
            "rust": [".rs"],
            "php": [".php", ".phtml", ".php3", ".php4", ".php5"],
            "ruby": [".rb", ".rbw"],
            "swift": [".swift"],
            "kotlin": [".kt", ".kts"],
            "scala": [".scala", ".sc"],
            "r": [".r", ".R"],
            "matlab": [".m"],
            "shell": [".sh", ".bash", ".zsh", ".fish"],
            "powershell": [".ps1", ".psm1", ".psd1"],
            "sql": [".sql"],
            "html": [".html", ".htm", ".xhtml"],
            "css": [".css", ".scss", ".sass", ".less"],
            "xml": [".xml", ".xsd", ".xslt"],
            "yaml": [".yaml", ".yml"],
            "json": [".json"],
            "markdown": [".md", ".markdown"],
            "dockerfile": ["Dockerfile", "dockerfile"],
            "cmake": ["CMakeLists.txt", ".cmake"],
            "makefile": ["Makefile", "makefile", ".mk"],
        }
        self.exclude_dirs = {
            ".git", ".svn", ".hg", "node_modules", "__pycache__", ".pytest_cache",
            "build", "dist", "target", "bin", "obj", ".vs", ".idea", ".vscode",
            "logs", "tmp", "temp", "cache", ".cache", "venv", "env", ".env",
            "coverage", ".coverage", "site-packages", ".tox", ".mypy_cache",
        }
        self.exclude_file_patterns = {
            ".DS_Store", "Thumbs.db", "*.tmp", "*.bak", "*.log", "*.o", "*.a",
            "*.so", "*.dll", "*.exe", "*.class", "*.pyc", "*.pyo", "*.pyd",
            "*.egg-info", "*.whl", "*.tar.gz", "*.zip", "*.rar",
        }
        self.language_weights = {
            "python": 1.0, "java": 1.0, "cpp": 1.0, "c": 0.8, "javascript": 0.9,
            "go": 1.0, "rust": 1.0, "php": 0.9, "ruby": 0.9, "swift": 1.0,
            "kotlin": 1.0, "scala": 1.0, "r": 0.8, "matlab": 0.8, "shell": 0.6,
            "powershell": 0.6, "sql": 0.5, "html": 0.4, "css": 0.4, "xml": 0.3,
            "yaml": 0.3, "json": 0.2, "markdown": 0.2, "dockerfile": 0.3,
            "cmake": 0.3, "makefile": 0.3,
        }

    def detect_language(self, project_path: str) -> str:
        project_dir = Path(project_path)
        if not project_dir.exists() or not project_dir.is_dir():
            raise ValueError(f"项目路径不存在或不是目录: {project_path}")

        language_counts = Counter()
        for file_path in project_dir.rglob("*"):
            if file_path.is_file() and self._should_exclude_file(file_path):
                continue
            if not file_path.is_file():
                continue
            file_extension = file_path.suffix.lower()
            file_name = file_path.name
            for lang in self._get_languages_by_extension(file_extension, file_name):
                language_counts[lang] += 1

        language_counts = self._handle_c_cpp_conflict(language_counts)
        weighted_scores = self._calculate_weighted_scores(language_counts)

        if not language_counts:
            raise ValueError("未检测到任何代码文件，无法确定项目语言类型")

        return max(weighted_scores, key=weighted_scores.get)

    def _get_languages_by_extension(self, file_extension: str, file_name: str) -> List[str]:
        languages = []
        for language, extensions in self.language_extensions.items():
            if file_extension in extensions:
                languages.append(language)
        if file_name in ["Dockerfile", "dockerfile"]:
            languages.append("dockerfile")
        elif file_name == "CMakeLists.txt":
            languages.append("cmake")
        elif file_name in ["Makefile", "makefile"]:
            languages.append("makefile")
        return languages

    def _should_exclude_file(self, file_path: Path) -> bool:
        file_name = file_path.name
        for pattern in self.exclude_file_patterns:
            if pattern.startswith("*."):
                if file_name.endswith(pattern[1:]):
                    return True
            elif file_name == pattern:
                return True
        for part in file_path.parts:
            if part in self.exclude_dirs:
                return True
        return False

    def _handle_c_cpp_conflict(self, language_counts: Counter) -> Counter:
        if language_counts.get("c", 0) > 0 and language_counts.get("cpp", 0) > 0:
            if language_counts["cpp"] >= language_counts["c"]:
                language_counts["cpp"] += language_counts["c"]
                del language_counts["c"]
            else:
                language_counts["c"] += language_counts["cpp"]
                del language_counts["cpp"]
        return language_counts

    def _calculate_weighted_scores(self, language_counts: Counter) -> Dict[str, float]:
        return {
            lang: count * self.language_weights.get(lang, 0.5)
            for lang, count in language_counts.items()
        }


def main():
    """主函数"""
    logger = get_logger("get_code_type")
    parser = argparse.ArgumentParser(description="代码库语言类型识别工具")
    parser.add_argument("project_path", nargs="?", help="代码库路径")
    parser.add_argument("output_dir", nargs="?", help="输出文件夹路径")
    parser.add_argument("--output", "-o", help="输出文件路径（可选）")
    parser.add_argument("--list-languages", action="store_true", help="列出支持的语言")
    args = parser.parse_args()

    detector = CodeLanguageDetector()
    if args.list_languages:
        for lang in detector.language_extensions:
            print(f"  {lang}: {detector.language_extensions[lang]}")
        return

    if not args.project_path:
        logger.error("未提供代码库路径")
        parser.print_help()
        sys.exit(1)

    try:
        detected_language = detector.detect_language(args.project_path)
    except ValueError as e:
        logger.error("语言检测失败: %s", e)
        sys.exit(1)

    if args.output_dir:
        output_path = Path(args.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        result = {
            "language": detected_language,
            "project_path": str(Path(args.project_path).resolve()),
            "detected_at": str(Path.cwd()),
            "related_json_files": [],
        }
        code_type_file = output_path / "code_type.json"
        with open(code_type_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        logger.info("检测结果已保存到: %s", code_type_file)
    elif args.output:
        result = {
            "project_path": args.project_path,
            "detected_language": detected_language,
            "timestamp": str(Path.cwd()),
        }
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
    else:
        print(detected_language)


if __name__ == "__main__":
    main()
