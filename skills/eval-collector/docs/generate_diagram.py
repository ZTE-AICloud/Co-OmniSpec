#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
eval-collector 架构图生成脚本
使用 matplotlib 生成架构图
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np

def draw_box(ax, x, y, width, height, label, sublabel='', color='#4A90E2', fontsize=10):
    """绘制圆角矩形框"""
    box = FancyBboxPatch((x, y), width, height,
                         boxstyle="round,pad=0.02,rounding_size=0.1",
                         facecolor=color, edgecolor='#333333', linewidth=1.5,
                         alpha=0.8)
    ax.add_patch(box)

    if sublabel:
        ax.text(x + width/2, y + height/2 + 0.08, label,
                ha='center', va='center', fontsize=fontsize, fontweight='bold', color='white')
        ax.text(x + width/2, y + height/2 - 0.08, sublabel,
                ha='center', va='center', fontsize=fontsize-2, color='white')
    else:
        ax.text(x + width/2, y + height/2, label,
                ha='center', va='center', fontsize=fontsize, fontweight='bold', color='white')

def draw_arrow(ax, start, end, color='#555555'):
    """绘制箭头连接"""
    ax.annotate('', xy=end, xytext=start,
                arrowprops=dict(arrowstyle='->', color=color, lw=1.5))

def generate_architecture_diagram():
    """生成 eval-collector 架构图"""
    fig, ax = plt.subplots(1, 1, figsize=(14, 10))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 10)
    ax.set_aspect('equal')
    ax.axis('off')

    # 标题
    ax.text(7, 9.5, 'eval-collector Skill 架构图', ha='center', va='center',
            fontsize=18, fontweight='bold', color='#2C3E50')
    ax.text(7, 9.0, 'SDD流程代码变更采集', ha='center', va='center',
            fontsize=13, color='#7F8C8D')

    # ========== 输入层 ==========
    draw_box(ax, 0.3, 7.3, 2.8, 0.9, '输入层', '--repo-root', '#3498DB', 11)
    draw_box(ax, 0.3, 6.2, 2.8, 0.9, '', '--target-dir', '#3498DB', 11)
    draw_box(ax, 0.3, 5.1, 2.8, 0.9, '', '--branch', '#3498DB', 11)

    # ========== Git 仓库层 ==========
    draw_box(ax, 3.5, 6.8, 3.0, 1.4, 'Git 仓库层', 'git diff/ls-files', '#E67E22', 11)
    draw_box(ax, 3.5, 5.1, 3.0, 0.9, 'get_changed_files()', '', '#E67E22', 11)

    # ========== 解析层 ==========
    draw_box(ax, 7.0, 7.5, 3.2, 1.0, 'split_diff_by_file()', '', '#9B59B6', 11)
    draw_box(ax, 7.0, 6.3, 3.2, 1.0, 'extract_code_snippets()', '', '#9B59B6', 11)
    draw_box(ax, 7.0, 5.1, 3.2, 1.0, 'parse_feature_infos()', '', '#9B59B6', 11)

    # ========== tasks.md ==========
    draw_box(ax, 10.8, 5.1, 2.8, 2.5, 'tasks.md', '**目的**: xxx', '#F39C12', 11)

    # ========== 构建层 ==========
    draw_box(ax, 3.5, 3.6, 3.0, 1.0, 'build_code_blocks()', '', '#27AE60', 11)
    draw_box(ax, 3.5, 2.4, 3.0, 1.0, 'build_payload()', '', '#27AE60', 11)

    # ========== JSON 结构 ==========
    draw_box(ax, 7.0, 2.4, 3.2, 2.2, 'JSON 结构', 'api + input', '#1ABC9C', 12)

    # ========== 输出层 ==========
    draw_box(ax, 7.0, 0.8, 3.2, 1.2, '输出层', '', '#E74C3C', 12)

    # ========== 输出目录 ==========
    draw_box(ax, 10.8, 0.8, 2.8, 1.2, 'changes/{branch}/evalset/', '', '#C0392B', 11)

    # ========== 箭头连接 ==========
    # 输入 -> Git
    draw_arrow(ax, (3.1, 7.7), (3.5, 7.5))
    draw_arrow(ax, (3.1, 6.6), (3.5, 6.5))
    draw_arrow(ax, (3.1, 5.5), (3.5, 5.5))

    # Git -> 解析层
    draw_arrow(ax, (6.5, 7.5), (7.0, 7.5))
    draw_arrow(ax, (6.5, 6.5), (7.0, 6.5))
    draw_arrow(ax, (6.5, 5.5), (7.0, 5.5))

    # tasks.md -> parse_feature_infos
    draw_arrow(ax, (10.8, 6.5), (10.2, 5.8))

    # Git -> build_code_blocks
    draw_arrow(ax, (5.0, 5.1), (5.0, 4.4))

    # build_code_blocks -> build_payload
    draw_arrow(ax, (5.0, 3.6), (5.0, 3.2))

    # build_payload -> JSON
    draw_arrow(ax, (6.5, 2.9), (7.0, 3.0))

    # JSON -> 输出层
    draw_arrow(ax, (8.6, 2.4), (8.6, 1.8))

    # 输出层 -> 目录
    draw_arrow(ax, (9.4, 0.8), (10.8, 1.2))

    # ========== 图例 ==========
    ax.text(0.3, 0.5, '数据流:', fontsize=11, fontweight='bold', color='#2C3E50')
    ax.annotate('', xy=(1.3, 0.3), xytext=(0.3, 0.3),
                arrowprops=dict(arrowstyle='->', color='#555555', lw=1.5))
    ax.text(1.5, 0.3, '处理流程', fontsize=10, color='#555555')

    # 配色说明
    ax.text(3.5, 0.5, '配色说明:', fontsize=11, fontweight='bold', color='#2C3E50')
    patches = [
        mpatches.Patch(color='#3498DB', label='输入参数'),
        mpatches.Patch(color='#E67E22', label='Git操作'),
        mpatches.Patch(color='#9B59B6', label='解析函数'),
        mpatches.Patch(color='#27AE60', label='构建函数'),
        mpatches.Patch(color='#1ABC9C', label='JSON结构'),
        mpatches.Patch(color='#E74C3C', label='输出'),
    ]
    ax.legend(handles=patches, loc='lower right', fontsize=10, framealpha=0.9)

    plt.tight_layout()
    output_path = 'D:/Users/10255643.WIN-23U9JM8071V/Desktop/战训营/plugin-test/.claude/skills/eval-collector/docs/architecture.png'
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
    print(f"架构图已生成: {output_path}")
    plt.close()

if __name__ == '__main__':
    generate_architecture_diagram()
