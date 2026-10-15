#!/usr/bin/env node
// 校验 skills-manifest.json，并校验仓库内所有 SKILL.md 的 frontmatter。
// 用法：node scripts/validate-manifest.mjs [仓库根目录，默认当前目录]
import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import { join, relative, resolve } from "node:path";
import { pathToFileURL } from "node:url";

/** 解析 SKILL.md 开头的简单 YAML frontmatter（key: value），无 frontmatter 返回 null */
export function parseFrontmatter(text) {
  const m = text.replace(/^\uFEFF/, "").match(/^---\r?\n([\s\S]*?)\r?\n---(?:\r?\n|$)/);
  if (!m) return null;
  const fm = {};
  for (const line of m[1].split(/\r?\n/)) {
    const kv = line.match(/^([A-Za-z_][\w-]*):\s*(.*)$/);
    if (kv) fm[kv[1]] = kv[2].trim().replace(/^["']|["']$/g, "");
  }
  return fm;
}

/** @returns {string[]} 错误列表 */
export function validateFrontmatter(text, label) {
  const fm = parseFrontmatter(text);
  if (!fm) return [`${label}: 缺少 YAML frontmatter（--- 包裹）`];
  const errs = [];
  if (!fm.name) errs.push(`${label}: frontmatter 缺少 name`);
  else if (!/^[a-z0-9]+(-[a-z0-9]+)*$/.test(fm.name)) errs.push(`${label}: name "${fm.name}" 应为 kebab-case`);
  if (!fm.description) errs.push(`${label}: frontmatter 缺少 description`);
  return errs;
}

/**
 * @param {any} manifest
 * @param {(p:string)=>string|null} readFile 读取相对路径文本，不存在返回 null
 */
export function validateManifest(manifest, readFile) {
  const errs = [];
  if (!manifest || typeof manifest !== "object") return ["manifest 必须是对象"];
  if (!/^\d+\.\d+\.\d+$/.test(manifest.version ?? "")) errs.push("version 必须是 semver（如 1.0.0）");
  if (!Array.isArray(manifest.skills) || manifest.skills.length === 0) return [...errs, "skills 必须是非空数组"];
  const ids = new Set();
  manifest.skills.forEach((s, i) => {
    const tag = `skills[${i}]`;
    for (const k of ["id", "title", "type", "path", "description"])
      if (typeof s[k] !== "string" || !s[k].trim()) errs.push(`${tag}: 缺少字符串字段 ${k}`);
    if (s.id) {
      if (!/^[a-z0-9]+(-[a-z0-9]+)*$/.test(s.id)) errs.push(`${tag}: id "${s.id}" 应为 kebab-case`);
      if (ids.has(s.id)) errs.push(`${tag}: id "${s.id}" 重复`);
      ids.add(s.id);
    }
    if (s.type && !["doc", "skill"].includes(s.type)) errs.push(`${tag}: type 只能是 doc 或 skill`);
    if (s.path) {
      const text = readFile(s.path);
      if (text === null) errs.push(`${tag}: path "${s.path}" 文件不存在`);
      else if (s.type === "skill") errs.push(...validateFrontmatter(text, s.path));
    }
    if (s.tags !== undefined && !(Array.isArray(s.tags) && s.tags.every((t) => typeof t === "string"))) errs.push(`${tag}: tags 必须是字符串数组`);
  });
  return errs;
}

function findSkillFiles(dir, out = []) {
  for (const f of readdirSync(dir)) {
    if (f === ".git" || f === "node_modules") continue;
    const p = join(dir, f);
    if (statSync(p).isDirectory()) findSkillFiles(p, out);
    else if (f === "SKILL.md") out.push(p);
  }
  return out;
}

function main() {
  const root = resolve(process.argv[2] || ".");
  const errs = [];
  const mp = join(root, "skills-manifest.json");
  if (!existsSync(mp)) errs.push("找不到 skills-manifest.json");
  else {
    let manifest;
    try { manifest = JSON.parse(readFileSync(mp, "utf8")); } catch (e) { errs.push(`skills-manifest.json 不是合法 JSON: ${e.message}`); }
    if (manifest) {
      const fp = (p) => (existsSync(join(root, p)) ? readFileSync(join(root, p), "utf8") : null);
      errs.push(...validateManifest(manifest, fp));
      // 所有 SKILL.md 必须登记在 manifest 中
      const listed = new Set((manifest.skills || []).map((s) => s.path));
      for (const f of findSkillFiles(root)) {
        const rel = relative(root, f).split("\\").join("/");
        errs.push(...validateFrontmatter(readFileSync(f, "utf8"), rel));
        if (!listed.has(rel)) errs.push(`${rel}: 未登记在 skills-manifest.json`);
      }
    }
  }
  errs.forEach((e) => console.log(`ERROR ${e}`));
  console.log(errs.length ? `校验失败：${errs.length} 个错误` : "校验通过");
  process.exit(errs.length ? 1 : 0);
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) main();
