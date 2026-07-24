#!/usr/bin/env node
/**
 * 验证技能插件结构
 */
const fs = require('fs');
const path = require('path');

const skillsDir = path.join(__dirname, '../skills');

if (!fs.existsSync(skillsDir)) {
  console.error('skills 目录不存在');
  process.exit(1);
}

const skills = fs.readdirSync(skillsDir)
  .filter(name => {
    const skillPath = path.join(skillsDir, name);
    return fs.statSync(skillPath).isDirectory();
  });

let valid = 0;
let invalid = 0;

skills.forEach(name => {
  const skillPath = path.join(skillsDir, name);
  const files = fs.readdirSync(skillPath);

  const hasSkillMd = files.some(f => f.endsWith('.md'));
  const hasConfig = files.some(f => f === 'skill.json' || f === 'config.yaml');

  if (hasSkillMd) {
    valid++;
    console.log(`[OK] ${name}`);
  } else {
    invalid++;
    console.log(`[FAIL] ${name} - 缺少 .md 文件`);
  }
});

console.log(`\n验证完成: ${valid} 有效, ${invalid} 无效`);