#!/usr/bin/env python3
import re
import uuid
from typing import Dict, List, Any, Optional, Tuple

# 导入常量
try:
    from ..constants import UUID_SEPARATOR
except ImportError:
    from constants import UUID_SEPARATOR

class AnnotationParser:
    """Java注解解析器"""
    
    def __init__(self):
        self.annotation_patterns = {
            # 标准注解
            'Override': r'@Override',
            'Deprecated': r'@Deprecated',
            'SuppressWarnings': r'@SuppressWarnings\s*\(\s*["\']([^"\']*)["\']?\s*\)',
            'FunctionalInterface': r'@FunctionalInterface',
            'SafeVarargs': r'@SafeVarargs',
            
            # Spring框架注解
            'Component': r'@Component(?:\s*\(\s*["\']([^"\']*)["\']?\s*\))?',
            'Service': r'@Service(?:\s*\(\s*["\']([^"\']*)["\']?\s*\))?',
            'Repository': r'@Repository(?:\s*\(\s*["\']([^"\']*)["\']?\s*\))?',
            'Controller': r'@Controller(?:\s*\(\s*["\']([^"\']*)["\']?\s*\))?',
            'RestController': r'@RestController(?:\s*\(\s*["\']([^"\']*)["\']?\s*\))?',
            'RequestMapping': r'@RequestMapping\s*\(\s*([^)]*)\s*\)',
            'GetMapping': r'@GetMapping\s*\(\s*["\']([^"\']*)["\']?\s*\)',
            'PostMapping': r'@PostMapping\s*\(\s*["\']([^"\']*)["\']?\s*\)',
            'PutMapping': r'@PutMapping\s*\(\s*["\']([^"\']*)["\']?\s*\)',
            'DeleteMapping': r'@DeleteMapping\s*\(\s*["\']([^"\']*)["\']?\s*\)',
            'Autowired': r'@Autowired',
            'Qualifier': r'@Qualifier\s*\(\s*["\']([^"\']*)["\']?\s*\)',
            'Value': r'@Value\s*\(\s*["\']([^"\']*)["\']?\s*\)',
            
            # JPA注解
            'Entity': r'@Entity(?:\s*\(\s*["\']([^"\']*)["\']?\s*\))?',
            'Table': r'@Table\s*\(\s*([^)]*)\s*\)',
            'Id': r'@Id',
            'GeneratedValue': r'@GeneratedValue\s*\(\s*([^)]*)\s*\)',
            'Column': r'@Column\s*\(\s*([^)]*)\s*\)',
            'JoinColumn': r'@JoinColumn\s*\(\s*([^)]*)\s*\)',
            'OneToMany': r'@OneToMany\s*\(\s*([^)]*)\s*\)',
            'ManyToOne': r'@ManyToOne\s*\(\s*([^)]*)\s*\)',
            'ManyToMany': r'@ManyToMany\s*\(\s*([^)]*)\s*\)',
            
            # 验证注解
            'NotNull': r'@NotNull',
            'NotEmpty': r'@NotEmpty',
            'NotBlank': r'@NotBlank',
            'Valid': r'@Valid',
            'Size': r'@Size\s*\(\s*([^)]*)\s*\)',
            'Min': r'@Min\s*\(\s*(\d+)\s*\)',
            
            # 元注解
            'Retention': r'@Retention\s*\(\s*([^)]*)\s*\)',
            'Target': r'@Target\s*\(\s*([^)]*)\s*\)',
            'Documented': r'@Documented',
            'Inherited': r'@Inherited',
            'Repeatable': r'@Repeatable\s*\(\s*([^)]*)\s*\)',
            'Max': r'@Max\s*\(\s*(\d+)\s*\)',
            
            # 其他常用注解
            'Transactional': r'@Transactional(?:\s*\(\s*([^)]*)\s*\))?',
            'Async': r'@Async',
            'Scheduled': r'@Scheduled\s*\(\s*([^)]*)\s*\)',
            'EventListener': r'@EventListener',
            'JsonProperty': r'@JsonProperty\s*\(\s*["\']([^"\']*)["\']?\s*\)',
            'JsonIgnore': r'@JsonIgnore',
        }
    
    def extract_annotations_from_text(self, text: str, start_pos: int = 0, end_pos: int = None) -> List[Dict[str, Any]]:
        """从文本中提取注解信息"""
        if end_pos is None:
            end_pos = len(text)
        
        text_segment = text[start_pos:end_pos]
        annotations = []
        
        # 查找所有@符号开始的注解
        annotation_pattern = r'@(\w+(?:\.\w+)*)\s*(?:\(\s*([^)]*)\s*\))?'
        matches = re.finditer(annotation_pattern, text_segment)
        
        for match in matches:
            annotation_name = match.group(1)
            annotation_params = match.group(2) if match.group(2) else ""
            
            annotation_info = {
                "name": annotation_name,
                "params": self._parse_annotation_parameters(annotation_params),
                "raw_text": match.group(0).strip(),
                "position": start_pos + match.start(),
                "type": self._classify_annotation(annotation_name)
            }
            annotations.append(annotation_info)
        
        return annotations
    
    def _parse_annotation_parameters(self, params_text: str) -> Dict[str, Any]:
        """解析注解参数"""
        if not params_text.strip():
            return {}
        
        params = {}
        
        # 处理简单的value参数（如 @Value("${property.name}")）
        simple_value_pattern = r'^["\']([^"\']*)["\']$'
        simple_match = re.match(simple_value_pattern, params_text.strip())
        if simple_match:
            return {"value": simple_match.group(1)}
        
        # 处理复杂参数（如 name="value", path="/api"）
        param_pattern = r'(\w+)\s*=\s*([^,]+)'
        param_matches = re.finditer(param_pattern, params_text)
        
        for param_match in param_matches:
            param_name = param_match.group(1).strip()
            param_value = param_match.group(2).strip()
            
            # 去除引号
            if param_value.startswith('"') and param_value.endswith('"'):
                param_value = param_value[1:-1]
            elif param_value.startswith("'") and param_value.endswith("'"):
                param_value = param_value[1:-1]
            
            params[param_name] = param_value
        
        # 如果没有找到键值对，但有内容，则作为value处理
        if not params and params_text.strip():
            clean_value = params_text.strip()
            if clean_value.startswith('"') and clean_value.endswith('"'):
                clean_value = clean_value[1:-1]
            elif clean_value.startswith("'") and clean_value.endswith("'"):
                clean_value = clean_value[1:-1]
            params["value"] = clean_value
        
        return params
    
    def _classify_annotation(self, annotation_name: str) -> str:
        """分类注解类型"""
        spring_annotations = {
            'Component', 'Service', 'Repository', 'Controller', 'RestController',
            'RequestMapping', 'GetMapping', 'PostMapping', 'PutMapping', 'DeleteMapping',
            'Autowired', 'Qualifier', 'Value', 'Bean', 'Configuration'
        }
        
        jpa_annotations = {
            'Entity', 'Table', 'Id', 'GeneratedValue', 'Column', 'JoinColumn',
            'OneToMany', 'ManyToOne', 'ManyToMany', 'OneToOne', 'Transient'
        }
        
        validation_annotations = {
            'NotNull', 'NotEmpty', 'NotBlank', 'Valid', 'Size', 'Min', 'Max',
            'Pattern', 'Email', 'Past', 'Future'
        }
        
        standard_annotations = {
            'Override', 'Deprecated', 'SuppressWarnings', 'FunctionalInterface', 'SafeVarargs'
        }
        
        if annotation_name in spring_annotations:
            return "spring"
        elif annotation_name in jpa_annotations:
            return "jpa"
        elif annotation_name in validation_annotations:
            return "validation"
        elif annotation_name in standard_annotations:
            return "standard"
        else:
            return "custom"
    
    def parse_class_annotations(self, class_text: str, class_name: str, filename: str) -> Tuple[str, Dict[str, Any]]:
        """解析类级别的注解"""
        # 查找类声明之前的注解
        class_pattern = r'((?:@\w+(?:\.\w+)*(?:\s*\([^)]*\))?\s*\n?\s*)*)\s*(?:public|private|protected)?\s*(?:static\s+)?(?:final\s+)?(?:abstract\s+)?class\s+' + re.escape(class_name)
        
        match = re.search(class_pattern, class_text)
        if not match:
            return None, None
        
        annotations_text = match.group(1)
        annotations = self.extract_annotations_from_text(annotations_text)
        
        if not annotations:
            return None, None
        
        # 生成唯一ID
        unique_id = str(uuid.uuid4())
        annotation_key = f"class_annotations_{class_name}{UUID_SEPARATOR}{unique_id}"
        
        annotation_info = {
            "type": "annotation_definition",
            "target_type": "class",
            "target_name": class_name,
            "filename": filename,
            "name": f"class_annotations_{class_name}",
            "uuid": unique_id,
            "annotations": annotations,
            "annotation_count": len(annotations),
            "content": annotations_text.strip()
        }
        
        return annotation_key, annotation_info
    
    def parse_method_annotations(self, method_text: str, method_name: str, class_name: str, filename: str) -> Tuple[str, Dict[str, Any]]:
        """解析方法级别的注解"""
        # 查找方法声明之前的注解
        # 同时支持普通方法（有返回类型）和构造函数（无返回类型）
        method_pattern = r'((?:@\w+(?:\.\w+)*(?:\s*\([^)]*\))?\s*\n?\s*)*)\s*(?:public|private|protected)?\s*(?:static\s+)?(?:final\s+)?(?:synchronized\s+)?(?:abstract\s+)?(?:(?:\w+(?:<[^>]*>)?(?:\[\])?\s+)?)' + re.escape(method_name) + r'\s*\('
        
        match = re.search(method_pattern, method_text)
        if not match:
            return None, None
        
        annotations_text = match.group(1)
        annotations = self.extract_annotations_from_text(annotations_text)
        
        if not annotations:
            return None, None
        
        # 生成唯一ID
        unique_id = str(uuid.uuid4())
        annotation_key = f"method_annotations_{method_name}{UUID_SEPARATOR}{unique_id}"
        
        annotation_info = {
            "type": "annotation_definition",
            "target_type": "method",
            "target_name": method_name,
            "class_name": class_name,
            "filename": filename,
            "name": f"method_annotations_{method_name}",
            "uuid": unique_id,
            "annotations": annotations,
            "annotation_count": len(annotations),
            "content": annotations_text.strip()
        }
        
        return annotation_key, annotation_info
    
    def parse_field_annotations(self, field_text: str, field_name: str, class_name: str, filename: str) -> Tuple[str, Dict[str, Any]]:
        """解析字段级别的注解"""
        # 查找字段声明之前的注解
        field_pattern = r'((?:@\w+(?:\.\w+)*(?:\s*\([^)]*\))?\s*\n?\s*)*)\s*(?:public|private|protected)?\s*(?:static\s+)?(?:final\s+)?(?:\w+(?:<[^>]*>)?(?:\[\])?\s+)?' + re.escape(field_name)
        
        match = re.search(field_pattern, field_text)
        if not match:
            return None, None
        
        annotations_text = match.group(1)
        annotations = self.extract_annotations_from_text(annotations_text)
        
        if not annotations:
            return None, None
        
        # 生成唯一ID
        unique_id = str(uuid.uuid4())
        annotation_key = f"field_annotations_{field_name}{UUID_SEPARATOR}{unique_id}"
        
        annotation_info = {
            "type": "annotation_definition",
            "target_type": "field",
            "target_name": field_name,
            "class_name": class_name,
            "filename": filename,
            "name": f"field_annotations_{field_name}",
            "uuid": unique_id,
            "annotations": annotations,
            "annotation_count": len(annotations),
            "content": annotations_text.strip()
        }
        
        return annotation_key, annotation_info
    
    def extract_all_annotations_from_file(self, file_content: str, filename: str) -> Dict[str, Dict[str, Any]]:
        """从整个文件中提取所有注解"""
        all_annotations = {}
        
        # 提取类注解
        class_pattern = r'(?:public|private|protected)?\s*(?:static\s+)?(?:final\s+)?(?:abstract\s+)?class\s+(\w+)'
        class_matches = re.finditer(class_pattern, file_content)
        
        for class_match in class_matches:
            class_name = class_match.group(1)
            # 查找类声明前的内容
            class_start = class_match.start()
            class_context = file_content[max(0, class_start - 500):class_start + 100]
            
            annotation_key, annotation_info = self.parse_class_annotations(class_context, class_name, filename)
            if annotation_key and annotation_info:
                all_annotations[annotation_key] = annotation_info
        
        # 提取方法注解
        method_pattern = r'(?:public|private|protected)?\s*(?:static\s+)?(?:final\s+)?(?:synchronized\s+)?(?:abstract\s+)?(?:\w+(?:<[^>]*>)?(?:\[\])?\s+)?(\w+)\s*\([^)]*\)\s*(?:throws\s+[^{]+)?\s*[{;]'
        method_matches = re.finditer(method_pattern, file_content)
        
        for method_match in method_matches:
            method_name = method_match.group(1)
            # 不再跳过构造函数，构造函数的注解也需要被识别
                
            method_start = method_match.start()
            method_context = file_content[max(0, method_start - 300):method_start + 100]
            
            # 查找所属类
            class_name = self._find_containing_class(file_content, method_start)
            
            annotation_key, annotation_info = self.parse_method_annotations(method_context, method_name, class_name, filename)
            if annotation_key and annotation_info:
                all_annotations[annotation_key] = annotation_info
        
        # 提取字段注解
        field_pattern = r'(?:public|private|protected)?\s*(?:static\s+)?(?:final\s+)?(\w+(?:<[^>]*>)?(?:\[\])?)\s+(\w+)(?:\s*=\s*[^;]+)?;'
        field_matches = re.finditer(field_pattern, file_content)
        
        for field_match in field_matches:
            field_name = field_match.group(2)
            field_start = field_match.start()
            field_context = file_content[max(0, field_start - 200):field_start + 100]
            
            # 查找所属类
            class_name = self._find_containing_class(file_content, field_start)
            
            annotation_key, annotation_info = self.parse_field_annotations(field_context, field_name, class_name, filename)
            if annotation_key and annotation_info:
                all_annotations[annotation_key] = annotation_info
        
        return all_annotations
    
    def _find_containing_class(self, file_content: str, position: int) -> str:
        """查找包含指定位置的类名"""
        # 向前查找最近的类声明
        before_text = file_content[:position]
        class_pattern = r'(?:public|private|protected)?\s*(?:static\s+)?(?:final\s+)?(?:abstract\s+)?class\s+(\w+)'
        
        matches = list(re.finditer(class_pattern, before_text))
        if matches:
            return matches[-1].group(1)
        
        return "UnknownClass"
