#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实体抽取工具模块
提供独立的 LLM 调用和配置加载功能，不依赖 reverse 目录
"""

import os
import json
import yaml
import logging
import re
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    """LLM配置类"""
    provider: str = 'openai'
    api_key: str = ''
    api_url: str = ''
    model: str = 'gpt-4'
    temperature: float = 0.2
    max_tokens: int = 4096
    timeout: int = 60
    max_concurrent: int = 5
    max_retries: int = 3
    retry_delay: float = 1.0
    retry_backoff: float = 2.0


class ConfigLoader:
    """简化的配置加载器，独立于 reverse/tools"""
    
    def __init__(self, config_file: Optional[Path] = None, repo_root: Optional[Path] = None):
        """
        初始化配置加载器
        
        Args:
            config_file: 配置文件路径（可选）
            repo_root: 仓库根目录（可选，用于查找默认配置文件）
        """
        if config_file:
            self.config_file = Path(config_file)
        elif repo_root:
            # 尝试从 reverse/tools/config.yaml 读取
            self.config_file = repo_root / "reverse" / "tools" / "config.yaml"
        else:
            # 使用环境变量或默认值
            self.config_file = None
        
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        if self.config_file and self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                # 处理环境变量
                config = self._process_env_vars(config)
                logger.debug(f"配置文件加载成功: {self.config_file}")
                return config
            except Exception as e:
                logger.warning(f"加载配置文件失败: {e}，使用环境变量配置")
        
        # 如果配置文件不存在，使用环境变量或默认值
        return {
            'llm': {
                'provider': os.getenv('LLM_PROVIDER', 'openai'),
                'api_key': os.getenv('LLM_API_KEY', ''),
                'api_url': os.getenv('LLM_API_URL', ''),
                'model': os.getenv('LLM_MODEL', 'gpt-4'),
                'temperature': float(os.getenv('LLM_TEMPERATURE', '0.2')),
                'max_tokens': int(os.getenv('LLM_MAX_TOKENS', '4096'))
            }
        }
    
    def _process_env_vars(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """处理配置中的环境变量"""
        def replace_env_vars(value):
            if isinstance(value, str):
                pattern = r'\$\{([^}]+)\}'
                def replace_match(match):
                    env_var_content = match.group(1)
                    if ':' in env_var_content:
                        env_var, default_value = env_var_content.split(':', 1)
                        return os.environ.get(env_var, default_value)
                    else:
                        env_var = env_var_content
                        return os.environ.get(env_var, match.group(0))
                return re.sub(pattern, replace_match, value)
            elif isinstance(value, dict):
                return {k: replace_env_vars(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [replace_env_vars(item) for item in value]
            return value
        
        return replace_env_vars(config)
    
    def get(self, key: str, default=None) -> Any:
        """获取配置项"""
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
        
        return value
    
    def get_llm_config(self) -> LLMConfig:
        """获取LLM配置对象"""
        llm_config = self.config.get('llm', {})
        return LLMConfig(**llm_config)


class PromptLoader:
    """简化的Prompt模板加载器，独立于 reverse/tools"""
    
    def __init__(self, template_dir: str):
        """
        初始化Prompt加载器
        
        Args:
            template_dir: Prompt模板目录路径
        """
        self.template_dir = Path(template_dir)
        if not self.template_dir.exists():
            raise FileNotFoundError(f"Prompt模板目录不存在: {self.template_dir}")
        
        self.templates = {}
        logger.debug(f"Prompt加载器初始化: {self.template_dir}")
    
    def load_template(self, template_name: str) -> Dict[str, str]:
        """加载Prompt模板"""
        if template_name in self.templates:
            return self.templates[template_name]
        
        template_file = self.template_dir / f"{template_name}.md"
        if not template_file.exists():
            raise FileNotFoundError(f"Prompt模板文件不存在: {template_file}")
        
        with open(template_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 解析模板内容
        template = self._parse_template(content)
        self.templates[template_name] = template
        
        logger.debug(f"加载Prompt模板: {template_name}")
        return template
    
    def _parse_template(self, content: str) -> Dict[str, str]:
        """解析模板内容"""
        lines = content.split('\n')
        system_prompt = []
        user_prompt = []
        current_section = None
        
        in_output_format = False
        for line in lines:
            if '## 系统提示词' in line:
                current_section = 'system'
                in_output_format = False
                continue
            elif '## 用户提示词模板' in line:
                current_section = 'user'
                in_output_format = False
                continue
            elif line.startswith('# 接口详细分析Prompt模板'):
                continue
            
            if current_section == 'system':
                system_prompt.append(line)
            elif current_section == 'user':
                user_prompt.append(line)
        
        return {
            'system_prompt': '\n'.join(system_prompt).strip(),
            'user_prompt_template': '\n'.join(user_prompt).strip()
        }
    
    def render_user_prompt(self, template_name: str, **kwargs) -> str:
        """渲染用户提示词"""
        template = self.load_template(template_name)
        user_prompt_template = template['user_prompt_template']
        
        try:
            rendered = user_prompt_template.format(**kwargs)
        except KeyError as e:
            logger.error(f"模板变量缺失: {e}")
            raise ValueError(f"渲染Prompt时缺少变量: {e}")
        
        return rendered
    
    def get_system_prompt(self, template_name: str) -> str:
        """获取系统提示词"""
        template = self.load_template(template_name)
        return template['system_prompt']
    
    def get_full_prompts(self, template_name: str, **kwargs) -> Tuple[str, str]:
        """获取完整的Prompt（系统+用户）"""
        system_prompt = self.get_system_prompt(template_name)
        user_prompt = self.render_user_prompt(template_name, **kwargs)
        return system_prompt, user_prompt


class LLMCaller:
    """简化的LLM调用器，使用 reverse/tools 的 LLMProvider，但通过动态导入"""
    
    def __init__(self, config: ConfigLoader, prompt_loader: PromptLoader, repo_root: Optional[Path] = None):
        """
        初始化LLM调用器
        
        Args:
            config: 配置加载器
            prompt_loader: Prompt加载器
            repo_root: 仓库根目录（用于动态导入 LLMProvider）
        """
        self.config = config
        self.prompt_loader = prompt_loader
        self.repo_root = repo_root
        
        # 动态导入 LLMProvider（仅在运行时导入，不依赖 reverse 目录的代码结构）
        if repo_root:
            tools_dir = repo_root / "reverse" / "tools"
            if tools_dir.exists():
                import sys
                if str(tools_dir) not in sys.path:
                    sys.path.insert(0, str(tools_dir))
        
        # 延迟导入，避免在模块加载时出错
        self._llm_provider = None
        self._llm_provider_factory = None
    
    def _get_provider(self):
        """延迟加载 LLMProvider"""
        if self._llm_provider is None:
            try:
                # 动态导入 reverse/tools 下的 LLMProvider
                from utils.llm_provider import LLMProviderFactory  # type: ignore
                self._llm_provider_factory = LLMProviderFactory
                
                llm_config = self.config.get_llm_config()
                provider_name = llm_config.provider
                
                self._llm_provider = LLMProviderFactory.create(provider_name, llm_config)
                logger.info(f"LLM调用器初始化: {provider_name} - {llm_config.model}")
            except ImportError as e:
                logger.error(f"无法导入 LLMProvider: {e}")
                raise RuntimeError(f"LLMProvider 导入失败，请确保 reverse/tools/utils/llm_provider.py 存在: {e}")
        
        return self._llm_provider
    
    def call_with_template(self, template_name: str, **template_vars) -> str:
        """
        使用Prompt模板调用LLM
        
        Args:
            template_name: Prompt模板名称
            **template_vars: 模板变量
            
        Returns:
            LLM响应内容
        """
        # 获取完整的Prompt
        system_prompt, user_prompt = self.prompt_loader.get_full_prompts(
            template_name, **template_vars
        )
        
        logger.debug(f"调用LLM: 模板={template_name}")
        
        # 调用LLM
        provider = self._get_provider()
        response = provider.call(system_prompt, user_prompt)
        
        return response

