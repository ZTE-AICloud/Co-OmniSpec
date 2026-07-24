#!/usr/bin/env python3
import re
import uuid
from typing import Dict, List, Any, Optional, Tuple

# 导入常量
try:
    from ..constants import UUID_SEPARATOR
except ImportError:
    from constants import UUID_SEPARATOR

class MethodParser:
    """Java方法解析器"""
    
    def __init__(self):
        self.java_keywords = {
            'abstract', 'assert', 'boolean', 'break', 'byte', 'case', 'catch', 'char',
            'class', 'const', 'continue', 'default', 'do', 'double', 'else', 'enum',
            'extends', 'final', 'finally', 'float', 'for', 'goto', 'if', 'implements',
            'import', 'instanceof', 'int', 'interface', 'long', 'native', 'new',
            'package', 'private', 'protected', 'public', 'return', 'short', 'static',
            'strictfp', 'super', 'switch', 'synchronized', 'this', 'throw', 'throws',
            'transient', 'try', 'void', 'volatile', 'while'
        }
    
    def parse_method(self, method_text: str, class_name: str, filename: str) -> Tuple[str, Dict[str, Any]]:
        """解析单个方法"""
        # 方法模式
        method_pattern = r'''
            ((?:@[\w\.]+(?:\([^)]*\))?\s*\n?\s*)*)           # 注解（支持全限定名）
            ((?:public|private|protected)\s+)?          # 访问修饰符
            ((?:static\s+|final\s+|synchronized\s+|native\s+|abstract\s+)*) # 其他修饰符
            ([\w\.]+(?:<[^<>]*(?:<[^<>]*>[^<>]*)*>)?(?:\[\])*)\s+               # 返回类型（允许限定名和泛型）
            (\w+)\s*                                    # 方法名
            \(([^)]*)\)                                 # 参数列表
            (?:\s*throws\s+([^{]+?))?                   # throws子句
            \s*(\{|;)                                   # 方法体开始或抽象方法分号
        '''
        
        # 关键修复：启用 DOTALL 以支持多行方法签名（例如参数或注解换行）
        match = re.search(method_pattern, method_text, re.VERBOSE | re.MULTILINE | re.DOTALL)
        
        if not match:
            return None, None
        
        annotations_text = match.group(1).strip()
        access_modifier = (match.group(2) or "package").strip()
        other_modifiers = match.group(3).strip()
        return_type = match.group(4).strip()
        method_name = match.group(5)
        params_text = match.group(6).strip()
        throws_clause = match.group(7).strip() if match.group(7) else ""
        body_start = match.group(8)
        
        # 验证：跳过Java关键字作为返回类型或方法名的情况
        return_type_clean = return_type.split('<')[0].split('[')[0].strip() if return_type else ""
        method_name_clean = method_name.strip() if method_name else ""
        
        if method_name_clean in self.java_keywords:
            return None, None
        
        # 如果返回类型是Java关键字（除了void和boolean），跳过此匹配
        if return_type_clean in self.java_keywords and return_type_clean not in ("void", "boolean"):
            return None, None
        
        # 额外验证：跳过 "new" 作为返回类型的情况（new ClassName() 被误识别为方法）
        if return_type_clean == "new":
            return None, None
        
        # 额外验证：如果方法名首字母大写且返回类型是 "new"，很可能是 new ClassName() 的误匹配
        if (method_name_clean and 
            method_name_clean[0].isupper() and 
            return_type_clean == "new"):
            return None, None
        
        # 生成唯一ID
        unique_id = str(uuid.uuid4())
        method_key = f"{method_name}{UUID_SEPARATOR}{unique_id}"
        
        # 提取完整的方法体
        method_body = method_text
        if body_start == '{':
            method_body = self._extract_complete_method_body(method_text, match.start())
        
        method_info = {
            "type": "method_definition",
            "content": method_body,
            "filename": filename,
            "name": method_name,
            "uuid": unique_id,
            "class_name": class_name,
            "return_type": return_type,
            "params": self._parse_parameters(params_text),
            "access_modifier": access_modifier.replace(" ", "") if access_modifier else "package",
            "is_static": "static" in other_modifiers,
            "is_final": "final" in other_modifiers,
            "is_synchronized": "synchronized" in other_modifiers,
            "is_native": "native" in other_modifiers,
            "is_abstract": "abstract" in other_modifiers or body_start == ';',
            "is_constructor": method_name == class_name,
            "other_modifiers": other_modifiers,
            "throws_clause": throws_clause,
            "annotations": self._parse_annotations(annotations_text),
            "docstring": self._extract_javadoc(method_text, match.start()),
            "dependencies": self._extract_method_dependencies(method_body, method_name),
            "signature": self._build_signature(return_type, self._parse_parameters(params_text)),
            "lineno": self._calculate_line_number(method_text, match.start()),
            "end_lineno": self._calculate_line_number(method_text, match.start() + len(method_body)),
            "complexity_info": self._analyze_method_complexity(method_body)
        }
        
        return method_key, method_info
    
    def parse_all_methods_from_class(self, class_content: str, class_name: str, filename: str, static_import_methods=None) -> Dict[str, Dict[str, Any]]:
        """从类中解析所有方法（改进版 - 支持更多Java语法形式）"""
        methods = {}
        
                # 如果没有传入静态导入方法列表，则尝试从类内容中提取
        if static_import_methods is None:
            static_import_methods = self._extract_static_import_methods_from_class(class_content)
        
        # 改进的方法模式 - 支持更多Java语法形式
        method_pattern = r'''
        # 注意：方法体匹配改为只匹配签名部分，方法体通过后续代码手动提取
            # Javadoc（可选）
            # Javadoc（可选）
            ((?:/\*\*[\s\S]*?\*/\s*)?)
            
            # 注解（可选，支持多个和多行）
            ((?:@[\w\.]+(?:\([^)]*\))?\s*\n?\s*)*)
            
            # 访问修饰符（可选，支持package-private方法）
            ((?:public|private|protected)\s+)?
            
            # 其他修饰符（支持多个）
            ((?:(?:static|final|synchronized|native|abstract|strictfp|default)\s+)*)
            
            # 泛型方法参数（可选）
            (?:<([^<>]*(?:<[^<>]*>[^<>]*)*)>\s+)?
            
            # 返回类型（支持限定名、泛型和数组）
            ([\w\.]+(?:<[^<>]*(?:<[^<>]*>[^<>]*)*>)?(?:\[\])*)\s+
            
            # 方法名
            (\w+)\s*
            
            # 参数列表（支持复杂参数和跨行，使用非贪婪匹配处理嵌套括号）
            \(([\s\S]*?)\)
            
            # throws子句（可选）
            (?:\s*throws\s+([^{;]+?))?
            
            # 方法体开始标记（只匹配{或;，不匹配内容）
            \s*(\{|;)
        '''
        
        matches = re.finditer(method_pattern, class_content, re.VERBOSE | re.MULTILINE | re.DOTALL)
        seen_spans = set()
        seen_method_keys = set()  # (method_name, lineno)
        for match in matches:
            javadoc = match.group(1) or ""
            annotations_text = match.group(2) or ""
            access_modifier = (match.group(3) or "package").strip()
            other_modifiers = match.group(4) or ""
            generic_params = match.group(5)
            return_type = match.group(6)
            method_name = match.group(7)
            params_text = match.group(8)
            throws_clause = match.group(9) or ""
            body_start_char = match.group(10)
            method_body = match.group(10)
            
            # 跳过字段声明（误识别为方法）
            if body_start_char == ';' and '(' not in match.group(0).split(';')[0]:
                continue
            
            # 验证：跳过Java关键字作为返回类型或方法名的情况（例如：else if, if, for等）
            # 清理返回类型和方法名（去除可能的泛型参数和数组标记）
            return_type_clean = return_type.split('<')[0].split('[')[0].strip() if return_type else ""
            method_name_clean = method_name.strip() if method_name else ""
            
            # 关键修复：过滤静态导入方法调用被误识别为方法定义的情况
            if method_name_clean in static_import_methods and return_type_clean in ['return', 'throw']:
                print("跳过静态导入方法调用: {} (return type: {})".format(method_name_clean, return_type_clean))
                continue
                
            # 额外过滤：跳过明显的方法调用语句（return XXX(...)形式）
            if return_type_clean == 'return' and method_name_clean:
                # 这很可能是 return methodName(params); 语句，不是方法定义
                print("跳过return语句: return {}(...)".format(method_name_clean))
                continue
            
            # 如果方法名是Java关键字，跳过此匹配
            if method_name_clean in self.java_keywords:
                continue
            
            # 如果返回类型是Java关键字（除了void和boolean），跳过此匹配
            if return_type_clean in self.java_keywords and return_type_clean not in ("void", "boolean"):
                continue
            
            # 额外验证：跳过 "new" 作为返回类型的情况（new ClassName() 被误识别为方法）
            if return_type_clean == "new":
                continue
            
            # 额外验证：如果方法名首字母大写且返回类型是 "new"，很可能是 new ClassName() 的误匹配
            if (method_name_clean and 
                method_name_clean[0].isupper() and 
                return_type_clean == "new"):
                continue
            
            # 额外验证：检查匹配位置前是否有控制流关键字（else, if, for, while等）
            # 这有助于识别方法体内部的语句被误匹配的情况
            match_start = match.start()
            if match_start > 0:
                # 检查匹配位置前50个字符中是否有控制流关键字
                context_before = class_content[max(0, match_start - 50):match_start]
                # 查找紧邻的控制流关键字（后面跟着空格或换行）
                control_flow_pattern = r'\b(else|if|for|while|do|switch|case|catch|finally)\s+(?=\w)'
                if re.search(control_flow_pattern, context_before):
                    # 如果前面有控制流关键字，很可能是误匹配，跳过
                    continue
            
            # 手动提取完整的方法体（处理嵌套大括号）
            method_signature_end = match.end()
            if body_start_char == '{':
                # 提取完整的方法体（处理嵌套大括号）
                # method_signature_end - 1 是大括号的位置
                brace_pos = method_signature_end - 1
                method_body = self._extract_complete_method_body_from_position(class_content, brace_pos)
                if not method_body:
                    continue
                # 构建完整的方法内容：签名 + 方法体
                method_full_text = class_content[match.start():brace_pos + len(method_body)]
            else:
                # 抽象方法，只到分号
                method_body = ';'
                method_full_text = class_content[match.start():method_signature_end]
            
            # 生成唯一ID
            unique_id = str(uuid.uuid4())
            method_key = f"{method_name}{UUID_SEPARATOR}{unique_id}"
            
            method_info = {
                "type": "method_definition",
                "content": method_full_text,
                "filename": filename,
                "name": method_name,
                "uuid": unique_id,
                "class_name": class_name,
                "return_type": return_type,
                "generic_parameters": self._parse_generic_parameters(generic_params),
                "params": self._parse_parameters(params_text),
                "access_modifier": access_modifier.replace(" ", "") if access_modifier else "package",
                "is_static": "static" in other_modifiers,
                "is_final": "final" in other_modifiers,
                "is_synchronized": "synchronized" in other_modifiers,
                "is_native": "native" in other_modifiers,
                "is_abstract": "abstract" in other_modifiers or method_body == ';',
                "is_default": "default" in other_modifiers,
                "is_constructor": method_name == class_name,
                "other_modifiers": other_modifiers.strip(),
                "throws_clause": throws_clause.strip(),
                "annotations": self._parse_method_annotations(annotations_text),
                "docstring": self._extract_method_javadoc(javadoc),
                "dependencies": self._extract_method_dependencies(method_full_text, method_name),
                "signature": self._build_signature(return_type, self._parse_parameters(params_text)),
                "lineno": self._calculate_line_number(class_content, match.start()),
                "end_lineno": self._calculate_line_number(class_content, match.start() + len(method_full_text)),
                "complexity_info": self._analyze_method_complexity(method_body)
            }
            
            # 去重：按方法名+起始行号
            start_line = self._calculate_line_number(class_content, match.start())
            key_tuple = (method_name, start_line)
            if key_tuple in seen_method_keys:
                continue
            methods[method_key] = method_info
            seen_spans.add((match.start(), match.start() + len(method_full_text)))
            seen_method_keys.add(key_tuple)
        
        # 追加：针对Spring Mapping注解的方法进行专门兜底（避免极端换行/格式导致主模式漏检）
        # 识别 @GetMapping/@PostMapping/@DeleteMapping/@PutMapping/@PatchMapping 等（含全限定名）
        mapping_fallback = r'''
            (                               # 1) 注解块
                (?:
                    @[\w\.]*Mapping          # @XxxMapping 或全限定 @org...XxxMapping
                    \s*\([^)]*\)\s*          # (..)
                )+
            )
            ([\s\S]{0,200}?)                 # 2) 注解与方法签名之间允许少量字符（如其他注解、空白）
            (                                # 3) 方法签名（捕获整个签名以便后续提取）
                (?:(?:public|private|protected)\s+)?                                  # 访问修饰符（可选）
                (?:(?:static|final|synchronized|native|abstract|strictfp|default)\s+)* # 其他修饰符
                (?:<[^<>]*(?:<[^<>]*>[^<>]*)*>\s+)?                                   # 泛型方法参数（可选）
                [\w\.]+(?:<[^<>]*(?:<[^<>]*>[^<>]*)*>)?(?:\[\])*\s+                  # 返回类型
                (\w+)\s*                                                             # 方法名（捕获）
                \(([^)]*)\)                                                          # 参数
                (?:\s*throws\s+[^{;]+)?                                              # throws（可选）
                \s*(\{|;)                                                            # 方法体开始或分号
            )
        '''
        for m in re.finditer(mapping_fallback, class_content, re.VERBOSE | re.MULTILINE | re.DOTALL):
            # 跳过已覆盖范围
            span = (m.start(3), m.end(3))
            def _overlap(a, b):
                return not (a[1] <= b[0] or b[1] <= a[0])
            if any(_overlap(span, s) for s in seen_spans):
                continue
            
            method_name = m.group(4)
            params_text = m.group(5) or ""
            body_start_char = m.group(6)
            header_start = m.start(3)
            header_end = m.end(3)
            
            # 从签名位置提取完整方法体
            after_sig = class_content[header_end:]
            if body_start_char == '{':
                # 定位 '{' 在 header 内的相对位置
                brace_pos_in_header = class_content[header_start:header_end].rfind('{')
                if brace_pos_in_header == -1:
                    continue
                brace_abs_pos = header_start + brace_pos_in_header
                method_body = self._extract_complete_method_body_from_position(class_content, brace_abs_pos)
                if not method_body:
                    continue
                method_full_text = class_content[header_start: brace_abs_pos + len(method_body)]
            else:
                # 分号结束
                method_full_text = class_content[header_start: header_end]
            
            # 回溯返回类型（用于签名与展示）
            return_type = ""
            header_text = class_content[max(0, header_start-200):header_end]
            rt_match = re.search(
                r'(?:(?:public|private|protected)\s+)?'
                r'(?:(?:static|final|synchronized|native|abstract|strictfp|default)\s+)*'
                r'(?:<[^<>]*>\s+)?'
                r'([\w\.]+(?:<[^<>]*(?:<[^<>]*>[^<>]*)*>)?(?:\[\])*)\s+' + re.escape(method_name) + r'\s*\(',
                header_text
            )
            if rt_match:
                return_type = rt_match.group(1)
            
            # 去重：方法名+起始行号
            start_line = self._calculate_line_number(class_content, header_start)
            key_tuple = (method_name, start_line)
            if key_tuple in seen_method_keys:
                continue
            
            unique_id = str(uuid.uuid4())
            method_key = f"{method_name}{UUID_SEPARATOR}{unique_id}"
            methods[method_key] = {
                "type": "method_definition",
                "content": method_full_text,
                "filename": filename,
                "name": method_name,
                "uuid": unique_id,
                "class_name": class_name,
                "return_type": return_type or "",
                "generic_parameters": [],
                "params": self._parse_parameters(params_text),
                "access_modifier": "public",   # 映射方法通常为对外接口，保守设为public
                "is_static": False,
                "is_final": False,
                "is_synchronized": False,
                "is_native": False,
                "is_abstract": body_start_char != '{',
                "is_default": False,
                "is_constructor": method_name == class_name,
                "other_modifiers": "",
                "throws_clause": "",
                "annotations": [],  # 注解详细可由上游注解解析器补充
                "docstring": "",
                "dependencies": self._extract_method_dependencies(method_full_text, method_name),
                "signature": self._build_signature(return_type or "", self._parse_parameters(params_text)),
                "lineno": start_line,
                "end_lineno": self._calculate_line_number(class_content, header_start + len(method_full_text)),
                "complexity_info": {}
            }
            seen_spans.add(span)
            seen_method_keys.add(key_tuple)
        
        # 追加一次保守式兜底匹配，防止遗漏（例如复杂返回类型/换行导致主模式未命中）
        # 注意：支持没有访问修饰符的方法（package-private）
        fallback_pattern = r'''
            \s*
            (?:/\*\*[\s\S]*?\*/\s*)?                 # 可选Javadoc
            (?:@[\w\.]+(?:\([^)]*\))?\s*\n?\s*)*     # 可选注解（支持跨行）
            (?:(?:public|private|protected)\s+)?               # 访问修饰符（可选，支持package-private）
            (?:(?:static|final|synchronized|native|abstract|strictfp|default)\s+)*
            (?:<[^<>]*(?:<[^<>]*>[^<>]*)*>\s+)?           # 可选方法泛型
            [\w\.]+(?:<[^<>]*(?:<[^<>]*>[^<>]*)*>)?(?:\[\])*\s+  # 返回类型（含限定名/泛型/数组）
            (\w+)\s*                                     # 方法名
            \(([^)]*)\)                                  # 参数列表
        '''
        for m in re.finditer(fallback_pattern, class_content, re.VERBOSE | re.MULTILINE | re.DOTALL):
            # 跳过已覆盖的起止范围附近匹配
            span = (m.start(), m.end())
            def _overlap(a, b):
                return not (a[1] <= b[0] or b[1] <= a[0])
            if any(_overlap(span, s) for s in seen_spans):
                continue
            method_name = m.group(1)
            params_text = m.group(2) or ""
            
            # 验证：跳过Java关键字作为方法名的情况
            method_name_clean = method_name.strip() if method_name else ""
            if method_name_clean in self.java_keywords:
                continue
            
            # 额外验证：检查匹配位置前是否有控制流关键字
            match_start = m.start()
            if match_start > 0:
                context_before = class_content[max(0, match_start - 50):match_start]
                control_flow_pattern = r'\b(else|if|for|while|do|switch|case|catch|finally)\s+(?=\w)'
                if re.search(control_flow_pattern, context_before):
                    continue
            
            # 额外验证：检查匹配位置前是否有 "new" 关键字（new ClassName() 被误识别为方法）
            if match_start > 0:
                context_before = class_content[max(0, match_start - 10):match_start]
                if re.search(r'\bnew\s+' + re.escape(method_name_clean) + r'\s*\(', context_before):
                    continue
            
            # 额外验证：检查匹配位置前是否有注释符号（方法调用可能被误识别）
            if match_start > 0:
                context_before = class_content[max(0, match_start - 100):match_start]
                # 检查是否有单行注释 // 或多行注释 /* */，但需要排除方法定义前的注释
                # 如果注释后面跟着访问修饰符（public/private/protected），说明是方法定义前的注释，应该保留
                single_line_comment = re.search(r'//[^\n]*$', context_before, re.MULTILINE)
                if single_line_comment:
                    # 检查注释后是否有访问修饰符，如果没有，可能是方法调用前的注释
                    after_comment = context_before[single_line_comment.end():]
                    if not re.search(r'\b(public|private|protected)\s+', after_comment):
                        continue
                
                multi_line_comment = re.search(r'/\*[\s\S]*?\*/', context_before)
                if multi_line_comment:
                    # 检查注释后是否有访问修饰符，如果没有，可能是方法调用前的注释
                    after_comment = context_before[multi_line_comment.end():]
                    if not re.search(r'\b(public|private|protected)\s+', after_comment):
                        continue
                
                # 检查前面是否有赋值符号 = 或方法调用链 .method(（很可能是方法调用）
                if re.search(r'[=\.]\s*' + re.escape(method_name_clean) + r'\s*\(', context_before):
                    continue
            
            # 提取方法体或判定分号结束
            after_sig = class_content[m.end():]
            # 找到第一个非空白字符
            body_start_rel = None
            for idx, ch in enumerate(after_sig):
                if not ch.isspace():
                    body_start_rel = idx
                    break
            if body_start_rel is None:
                continue
            if after_sig[body_start_rel] == '{':
                # 计数大括号提取完整体
                brace_count = 0
                end_idx = body_start_rel
                for i in range(body_start_rel, len(after_sig)):
                    c = after_sig[i]
                    if c == '{':
                        brace_count += 1
                    elif c == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            end_idx = i + 1
                            break
                method_body_text = after_sig[:end_idx]
                method_full_text = class_content[m.start(): m.end() + end_idx]
                return_type = ""
                # 简单回溯返回类型（用于展示，不做严格解析）
                # 支持没有访问修饰符的方法
                header_text = class_content[max(0, m.start()-200):m.end()]
                rt_match = re.search(r'(?:(?:public|private|protected)\s+)?(?:(?:static|final|synchronized|native|abstract|strictfp|default)\s+)*(?:<[^>]*>\s+)?([\w\.]+(?:<[^<>]*(?:<[^<>]*>[^<>]*)*>)?(?:\[\])*)\s+' + re.escape(method_name) + r'\s*\(', header_text)
                if rt_match:
                    return_type = rt_match.group(1)

                return_type_clean = return_type.split('<')[0].split('[')[0].strip() if return_type else ""
                
                # 验证：如果返回类型为空或包含中文字符（可能是误匹配注释），跳过此匹配
                if not return_type_clean or any('\u4e00' <= c <= '\u9fff' for c in return_type_clean):
                    continue
                
                # 验证：如果返回类型是Java关键字（除了void和boolean），跳过此匹配
                if return_type_clean in self.java_keywords and return_type_clean not in ("void", "boolean"):
                    continue
                
                # 验证：如果返回类型是 "new"，跳过此匹配（new ClassName() 被误识别为方法）
                if return_type_clean == "new":
                    continue
                
                # 验证：如果方法名首字母大写且返回类型是 "new"，很可能是 new ClassName() 的误匹配
                if (method_name_clean and 
                    method_name_clean[0].isupper() and 
                    return_type_clean == "new"):
                    continue
                
                # 去重：方法名+行号
                start_line = self._calculate_line_number(class_content, m.start())
                key_tuple = (method_name, start_line)
                if key_tuple in seen_method_keys:
                    continue
                unique_id = str(uuid.uuid4())
                method_key = f"{method_name}{UUID_SEPARATOR}{unique_id}"
                methods[method_key] = {
                    "type": "method_definition",
                    "content": method_full_text,
                    "filename": filename,
                    "name": method_name,
                    "uuid": unique_id,
                    "class_name": class_name,
                    "return_type": return_type or "",
                    "generic_parameters": [],
                    "params": self._parse_parameters(params_text),
                    "access_modifier": "public",  # 兜底模式下保守值
                    "is_static": False,
                    "is_final": False,
                    "is_synchronized": False,
                    "is_native": False,
                    "is_abstract": False,
                    "is_default": False,
                    "is_constructor": method_name == class_name,
                    "other_modifiers": "",
                    "throws_clause": "",
                    "annotations": [],
                    "docstring": "",
                    "dependencies": self._extract_method_dependencies(method_full_text, method_name),
                    "signature": self._build_signature(return_type or "", self._parse_parameters(params_text)),
                    "lineno": start_line,
                    "end_lineno": self._calculate_line_number(class_content, m.start() + len(method_full_text)),
                    "complexity_info": self._analyze_method_complexity(method_body_text)
                }
                seen_spans.add(span)
                seen_method_keys.add(key_tuple)
            else:
                # 分号结束，视为抽象/接口方法
                end_semicolon = after_sig.find(';', body_start_rel)
                if end_semicolon == -1:
                    continue
                method_full_text = class_content[m.start(): m.end() + end_semicolon + 1]
                return_type = ""
                header_text = class_content[max(0, m.start()-200):m.end()]
                # 支持没有访问修饰符的方法
                rt_match = re.search(r'(?:(?:public|private|protected)\s+)?(?:(?:static|final|synchronized|native|abstract|strictfp|default)\s+)*(?:<[^>]*>\s+)?([\w\.]+(?:<[^<>]*(?:<[^<>]*>[^<>]*)*>)?(?:\[\])*)\s+' + re.escape(method_name) + r'\s*\(', header_text)
                if rt_match:
                    return_type = rt_match.group(1)
                
                return_type_clean = return_type.split('<')[0].split('[')[0].strip() if return_type else ""
                
                # 验证：如果返回类型为空或包含中文字符（可能是误匹配注释），跳过此匹配
                if not return_type_clean or any('\u4e00' <= c <= '\u9fff' for c in return_type_clean):
                    continue
                
                # 验证：如果返回类型是Java关键字（除了void和boolean），跳过此匹配
                if return_type_clean in self.java_keywords and return_type_clean not in ("void", "boolean"):
                    continue
                
                # 验证：如果返回类型是 "new"，跳过此匹配（new ClassName() 被误识别为方法）
                if return_type_clean == "new":
                    continue
                
                # 验证：如果方法名首字母大写且返回类型是 "new"，很可能是 new ClassName() 的误匹配
                if (method_name_clean and 
                    method_name_clean[0].isupper() and 
                    return_type_clean == "new"):
                    continue
                
                # 去重：方法名+行号
                start_line = self._calculate_line_number(class_content, m.start())
                key_tuple = (method_name, start_line)
                if key_tuple in seen_method_keys:
                    continue
                unique_id = str(uuid.uuid4())
                method_key = f"{method_name}{UUID_SEPARATOR}{unique_id}"
                methods[method_key] = {
                    "type": "method_definition",
                    "content": method_full_text,
                    "filename": filename,
                    "name": method_name,
                    "uuid": unique_id,
                    "class_name": class_name,
                    "return_type": return_type or "",
                    "generic_parameters": [],
                    "params": self._parse_parameters(params_text),
                    "access_modifier": "public",
                    "is_static": False,
                    "is_final": False,
                    "is_synchronized": False,
                    "is_native": False,
                    "is_abstract": True,
                    "is_default": False,
                    "is_constructor": method_name == class_name,
                    "other_modifiers": "",
                    "throws_clause": "",
                    "annotations": [],
                    "docstring": "",
                    "dependencies": [],
                    "signature": self._build_signature(return_type or "", self._parse_parameters(params_text)),
                    "lineno": start_line,
                    "end_lineno": self._calculate_line_number(class_content, m.start() + len(method_full_text)),
                    "complexity_info": {}
                }
                seen_spans.add(span)
                seen_method_keys.add(key_tuple)
        return methods
    
    def _extract_complete_method_body(self, method_text: str, start_pos: int) -> str:
        """提取完整的方法体"""
        # 查找第一个大括号的位置
        brace_start = method_text.find('{', start_pos)
        if brace_start == -1:
            return method_text  # 可能是抽象方法
        
        # 匹配大括号
        brace_count = 0
        method_end = brace_start
        
        for i in range(brace_start, len(method_text)):
            if method_text[i] == '{':
                brace_count += 1
            elif method_text[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    method_end = i + 1
                    break
        
        return method_text[:method_end]
    
    def _extract_complete_method_body_from_position(self, content: str, brace_start_pos: int) -> str:
        """从指定位置（大括号开始）提取完整的方法体，处理嵌套大括号和字符串"""
        if brace_start_pos >= len(content) or content[brace_start_pos] != '{':
            return None
        
        brace_count = 0
        in_string = False
        in_char = False
        escape_next = False
        
        for i in range(brace_start_pos, len(content)):
            char = content[i]
            
            if escape_next:
                escape_next = False
                continue
            
            if char == '\\':
                escape_next = True
                continue
            
            # 处理字符串字面量
            if char == '"' and not in_char:
                in_string = not in_string
                continue
            elif char == "'" and not in_string:
                in_char = not in_char
                continue
            
            # 只在非字符串上下文中计算大括号
            if not in_string and not in_char:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        return content[brace_start_pos:i + 1]
        
        # 如果没有找到匹配的结束大括号，返回None
        return None
    
    def _parse_generic_parameters(self, generic_text: str) -> List[str]:
        """解析泛型参数"""
        if not generic_text:
            return []
        
        params = []
        for param in generic_text.split(','):
            param = param.strip()
            if param:
                param_name = param.split()[0]
                params.append(param_name)
        
        return params
    
    def _parse_method_annotations(self, annotations_text: str) -> List[Dict[str, Any]]:
        """解析方法注解"""
        annotations = []
        annotation_pattern = r'@(\w+)(?:\(([^)]*)\))?'
        matches = re.finditer(annotation_pattern, annotations_text)
        
        for match in matches:
            annotation_name = match.group(1)
            annotation_params = match.group(2) or ""
            
            annotations.append({
                "name": annotation_name,
                "params": annotation_params,
                "raw_text": match.group(0)
            })
        
        return annotations
    
    def _extract_method_javadoc(self, javadoc_text: str) -> str:
        """提取方法Javadoc"""
        if not javadoc_text:
            return ""
        
        javadoc_match = re.search(r'/\*\*([\s\S]*?)\*/', javadoc_text)
        if javadoc_match:
            return javadoc_match.group(1).strip()
        return ""
    
    def _parse_parameters(self, params_text: str) -> List[Dict[str, Any]]:
        """解析方法参数"""
        if not params_text.strip():
            return []
        
        params = []
        
        # 分割参数，考虑泛型中的逗号
        param_parts = self._split_parameters(params_text)
        
        for part in param_parts:
            part = part.strip()
            if not part:
                continue
            
            # 解析单个参数
            param_info = self._parse_single_parameter(part)
            if param_info:
                params.append(param_info)
        
        return params
    
    def _split_parameters(self, params_text: str) -> List[str]:
        """智能分割参数列表，考虑泛型"""
        params = []
        current_param = ""
        bracket_count = 0
        
        for char in params_text:
            if char == '<':
                bracket_count += 1
            elif char == '>':
                bracket_count -= 1
            elif char == ',' and bracket_count == 0:
                params.append(current_param.strip())
                current_param = ""
                continue
            
            current_param += char
        
        if current_param.strip():
            params.append(current_param.strip())
        
        return params
    
    def _parse_single_parameter(self, param_text: str) -> Optional[Dict[str, Any]]:
        """解析单个参数"""
        # 参数模式：[final] [annotations] type name
        param_pattern = r'''
            (?:final\s+)?                              # 可选final
            (?:@\w+(?:\([^)]*\))?\s*)*                 # 可选注解
            (\w+(?:<[^>]*>)?(?:\.\.\.|(?:\[\])*)?)\s+  # 类型（支持泛型、可变参数、数组）
            (\w+)                                      # 参数名
        '''
        
        match = re.search(param_pattern, param_text.strip(), re.VERBOSE)
        if match:
            param_type = match.group(1)
            param_name = match.group(2)
            
            return {
                "name": param_name,
                "datatype": param_type,
                "is_final": "final" in param_text,
                "is_varargs": "..." in param_type,
                "annotations": self._extract_parameter_annotations(param_text)
            }
        
        return None
    
    def _extract_parameter_annotations(self, param_text: str) -> List[str]:
        """提取参数注解"""
        annotations = []
        annotation_pattern = r'@(\w+)(?:\([^)]*\))?'
        matches = re.finditer(annotation_pattern, param_text)
        
        for match in matches:
            annotations.append(match.group(1))
        
        return annotations
    
    def _parse_annotations(self, annotations_text: str) -> List[Dict[str, Any]]:
        """解析注解"""
        if not annotations_text.strip():
            return []
        
        annotations = []
        annotation_pattern = r'@(\w+(?:\.\w+)*)(?:\s*\(([^)]*)\))?'
        matches = re.finditer(annotation_pattern, annotations_text)
        
        for match in matches:
            annotation_name = match.group(1)
            annotation_params = match.group(2) if match.group(2) else ""
            
            annotations.append({
                "name": annotation_name,
                "params": annotation_params
            })
        
        return annotations
    
    def _extract_javadoc(self, content: str, method_start: int) -> str:
        """提取Javadoc注释"""
        # 向前查找Javadoc注释
        before_method = content[:method_start]
        javadoc_pattern = r'/\*\*(.*?)\*/'
        
        matches = list(re.finditer(javadoc_pattern, before_method, re.DOTALL))
        if matches:
            last_match = matches[-1]
            # 检查Javadoc是否紧邻方法
            between_text = before_method[last_match.end():].strip()
            if not between_text or all(line.strip().startswith('@') for line in between_text.split('\n')):
                return last_match.group(1).strip()
        
        return ""
    
    def _extract_method_dependencies(self, method_body: str, current_method_name: str = None) -> List[str]:
        """提取方法依赖 - 改进版"""
        dependencies = set()
        
        # 1. 提取方法调用 (完整的方法名) - 使用单词边界确保完整匹配
        method_call_pattern = r'(\w+)\.(\w+)\s*\('
        method_matches = re.finditer(method_call_pattern, method_body)
        for match in method_matches:
            class_or_obj = match.group(1)
            method_name = match.group(2)
            
            # 排除this和super，确保方法名完整
            if (class_or_obj not in ['this', 'super'] and 
                len(method_name) >= 3 and  # 确保至少3个字符
                method_name.replace('_', '').isalpha()):    # 允许下划线，但其他字符必须是字母
                dependencies.add(f"{class_or_obj}.{method_name}")
                # 如果是类名（首字母大写），也添加类依赖
                if class_or_obj[0].isupper():
                    dependencies.add(class_or_obj)
        
        # 2. 提取本地方法调用（没有类前缀的方法调用）
        local_method_pattern = r'(?:^|[\s;{,=(])\s*([a-z]\w+)\s*\([^)]*\)'
        local_method_matches = re.finditer(local_method_pattern, method_body, re.MULTILINE)
        for match in local_method_matches:
            method_name = match.group(1)
            # 排除Java关键字和常见的局部变量操作
            if (method_name not in self.java_keywords and 
                method_name not in ['get', 'set', 'is', 'has', 'to', 'of', 'for'] and
                len(method_name) > 3):  # 确保不是简单的操作符
                dependencies.add(method_name)
        
        # 3. 提取构造函数调用
        constructor_pattern = r'new\s+(\w+)(?:<[^>]*>)?\s*\('
        constructor_matches = re.finditer(constructor_pattern, method_body)
        for match in constructor_matches:
            class_name = match.group(1)
            if class_name[0].isupper():  # 确保是类名
                dependencies.add(class_name)
        
        # 4. 提取静态字段和枚举引用
        static_field_pattern = r'(\w+)\.(\w+)(?!\s*\()'
        static_matches = re.finditer(static_field_pattern, method_body)
        for match in static_matches:
            class_or_obj = match.group(1)
            field_name = match.group(2)
            
            # 排除this和super，确保字段名完整
            if (class_or_obj not in ['this', 'super'] and 
                len(field_name) >= 3 and      # 确保至少3个字符
                field_name.replace('_', '').isalpha()):       # 允许下划线，但其他字符必须是字母
                dependencies.add(f"{class_or_obj}.{field_name}")
                # 如果是类名（首字母大写），也添加类依赖
                if class_or_obj[0].isupper():
                    dependencies.add(class_or_obj)
        
        # 5. 提取局部变量声明中的类型（改进版）
        # 匹配: Type varName = ... 或 Type varName;
        local_var_pattern = r'(?:^|[\s;{])\s*(\w+)(?:<[^>]*>)?\s+(\w+)\s*(?:[=;])'
        local_var_matches = re.finditer(local_var_pattern, method_body, re.MULTILINE)
        for match in local_var_matches:
            type_name = match.group(1)
            var_name = match.group(2)
            if (type_name not in self.java_keywords and 
                type_name[0].isupper() and 
                type_name not in ['String', 'Integer', 'Boolean', 'Long', 'Double', 'Float', 'List', 'Map', 'Set'] and
                var_name not in ['String', 'Object']):  # 确保不是内置类型
                dependencies.add(type_name)
        
        # 6. 提取泛型参数中的类型
        generic_pattern = r'<([A-Z]\w+)(?:\s*,\s*([A-Z]\w+))*>'
        generic_matches = re.finditer(generic_pattern, method_body)
        for match in generic_matches:
            for i in range(1, match.lastindex + 1 if match.lastindex else 1):
                if match.group(i):
                    type_name = match.group(i)
                    if (type_name not in ['String', 'Integer', 'Boolean', 'Long', 'Double', 'Float', 'Object'] and
                        type_name[0].isupper()):
                        dependencies.add(type_name)
        
        # 7. 提取强制转换
        cast_pattern = r'\(\s*(\w+)\s*\)'
        cast_matches = re.finditer(cast_pattern, method_body)
        for match in cast_matches:
            type_name = match.group(1)
            if (type_name not in self.java_keywords and 
                type_name[0].isupper() and 
                type_name not in ['String', 'Integer', 'Boolean', 'Long', 'Double', 'Float']):
                dependencies.add(type_name)
        
        # 8. 补充类依赖（从方法调用中提取）
        class_deps_to_add = set()
        for dep in list(dependencies):  # 转换为列表避免修改时的问题
            if '.' in dep and not dep.endswith('.'):
                class_name = dep.split('.')[0]
                if (class_name[0].isupper() and 
                    class_name not in ['this', 'super'] and
                    len(class_name) > 2):
                    class_deps_to_add.add(class_name)
        
        # 添加类依赖
        for class_dep in class_deps_to_add:
            dependencies.add(class_dep)
        
        # 9. 过滤和清理依赖列表
        filtered_dependencies = set()
        for dep in dependencies:
            # 过滤掉太短的或明显错误的依赖
            if len(dep) >= 3 and not dep.endswith('.'):
                # 如果是类依赖（没有点号），直接保留
                if '.' not in dep:
                    filtered_dependencies.add(dep)
                else:
                    # 对于方法/字段依赖，检查是否是截断的版本
                    parts = dep.split('.')
                    if len(parts) == 2:
                        class_name, member_name = parts
                        # 检查是否有完整版本存在
                        is_truncated = False
                        for other_dep in dependencies:
                            if (other_dep != dep and 
                                other_dep.startswith(dep) and 
                                '.' in other_dep and
                                len(other_dep) > len(dep)):
                                # 检查是否是同一个成员的完整版本
                                other_parts = other_dep.split('.')
                                if (len(other_parts) == 2 and 
                                    other_parts[0] == class_name and
                                    other_parts[1].startswith(member_name)):
                                    is_truncated = True
                                    break
                        
                        if not is_truncated:
                            filtered_dependencies.add(dep)
        
        # 10. 过滤掉自己（递归调用）
        if current_method_name:
            filtered_dependencies = {dep for dep in filtered_dependencies 
                                   if dep != current_method_name}
        
        return list(filtered_dependencies)
    
    def _analyze_method_complexity(self, method_body: str) -> Dict[str, Any]:
        """分析方法复杂度"""
        if not method_body:
            return {}
        
        # 计算行数
        line_count = len(method_body.split('\n'))
        
        # 计算圈复杂度
        cyclomatic_complexity = self._calculate_cyclomatic_complexity(method_body)
        
        # 检查是否有嵌套
        has_nested_loops = self._has_nested_loops(method_body)
        has_nested_conditions = self._has_nested_conditions(method_body)
        
        # 计算参数数量（从方法签名中提取）
        param_pattern = r'\([^)]*\)'
        param_match = re.search(param_pattern, method_body)
        parameter_count = 0
        if param_match:
            params_text = param_match.group(0)[1:-1].strip()
            if params_text:
                parameter_count = len(self._split_parameters(params_text))
        
        return {
            "cyclomatic_complexity": cyclomatic_complexity,
            "line_count": line_count,
            "parameter_count": parameter_count,
            "has_nested_loops": has_nested_loops,
            "has_nested_conditions": has_nested_conditions,
            "has_try_catch": "try" in method_body and "catch" in method_body,
            "has_recursion": self._has_recursion(method_body)
        }
    
    def _calculate_cyclomatic_complexity(self, method_body: str) -> int:
        """计算圈复杂度"""
        complexity = 1  # 基础复杂度
        
        # 计算控制流语句
        patterns = [
            r'\bif\s*\(',          # if语句
            r'\belse\s+if\s*\(',   # else if语句
            r'\bwhile\s*\(',       # while循环
            r'\bfor\s*\(',         # for循环
            r'\bdo\s*\{',          # do-while循环
            r'\bswitch\s*\(',      # switch语句
            r'\bcase\s+',          # case分支
            r'\bcatch\s*\(',       # catch块
            r'\?\s*.*?\s*:',       # 三元运算符
            r'\&\&',               # 逻辑与
            r'\|\|'                # 逻辑或
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, method_body)
            complexity += len(list(matches))
        
        return complexity
    
    def _has_nested_loops(self, method_body: str) -> bool:
        """检查是否有嵌套循环"""
        loop_patterns = [r'\bfor\s*\(', r'\bwhile\s*\(', r'\bdo\s*\{']
        
        for pattern in loop_patterns:
            matches = list(re.finditer(pattern, method_body))
            if len(matches) > 1:
                return True
        
        return False
    
    def _has_nested_conditions(self, method_body: str) -> bool:
        """检查是否有嵌套条件"""
        if_count = len(re.findall(r'\bif\s*\(', method_body))
        return if_count > 2
    
    def _has_recursion(self, method_body: str) -> bool:
        """检查是否有递归调用"""
        # 简单检查：查找方法名的调用
        method_name_pattern = r'(\w+)\s*\('
        match = re.search(method_name_pattern, method_body)
        if match:
            method_name = match.group(1)
            return method_name in method_body[match.end():]
        
        return False
    
    def _calculate_line_number(self, content: str, position: int) -> int:
        """计算在内容中指定位置的行号"""
        lines_before = content[:position].count('\n')
        return lines_before + 1

    def _build_signature(self, return_type: str, params: List[Dict[str, Any]]) -> str:
        """构建方法签名字符串：(paramType1,paramType2)->returnType"""
        try:
            param_types = []
            for p in params or []:
                t = p.get("datatype", "?")
                # 规范化空白
                param_types.append(" ".join(t.split()))
            ret = " ".join((return_type or "void").split())
            return "({})-> {}".format(','.join(param_types), ret)
        except Exception:
            return "()->void"
    
    def _extract_static_import_methods_from_class(self, class_content):
        """从类内容中提取静态导入的方法名"""
        static_import_methods = set()
        # 匹配静态导入语句: import static com.package.Class.methodName;
        static_import_pattern = r'import\s+static\s+[\w\.]+\.(\w+)\s*;'
        matches = re.finditer(static_import_pattern, class_content)
        for match in matches:
            method_name = match.group(1)
            static_import_methods.add(method_name)
        return static_import_methods
