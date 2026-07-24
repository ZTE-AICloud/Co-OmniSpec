#!/usr/bin/env node
/**
 * 列出所有技能插件
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
  })
  .sort();

console.log(`共 ${skills.length} 个技能:\n`);
skills.forEach((name, index) => {
  console.log(`${String(index + 1).padStart(2, '0')}. ${name}`);
});