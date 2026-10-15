import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, existsSync } from "node:fs";
import { parseFrontmatter, validateFrontmatter, validateManifest } from "../scripts/validate-manifest.mjs";

const fsRead = (p) => (existsSync(p) ? readFileSync(p, "utf8") : null);
const entry = (o = {}) => ({ id: "a-b", title: "t", type: "doc", path: "README.md", description: "d", ...o });

test("仓库真实 manifest 通过校验", () => {
  const m = JSON.parse(readFileSync("skills-manifest.json", "utf8"));
  assert.deepEqual(validateManifest(m, fsRead), []);
});
test("parseFrontmatter", () => {
  assert.deepEqual(parseFrontmatter('---\nname: x-y\ndescription: "hello"\n---\nbody'), { name: "x-y", description: "hello" });
  assert.equal(parseFrontmatter("# no fm"), null);
});
test("frontmatter 缺字段 / 非 kebab-case", () => {
  assert.equal(validateFrontmatter("# x", "f").length, 1);
  assert.equal(validateFrontmatter("---\nname: A_B\n---\n", "f").length, 2);
  assert.deepEqual(validateFrontmatter("---\nname: ok-name\ndescription: d\n---\n", "f"), []);
});
test("manifest 各类错误", () => {
  const read = () => "x";
  assert.ok(validateManifest({ version: "1", skills: [entry()] }, read).some((e) => e.includes("semver")));
  assert.ok(validateManifest({ version: "1.0.0", skills: [] }, read).length === 1);
  assert.ok(validateManifest({ version: "1.0.0", skills: [entry(), entry()] }, read).some((e) => e.includes("重复")));
  assert.ok(validateManifest({ version: "1.0.0", skills: [entry({ type: "x" })] }, read).some((e) => e.includes("type")));
  assert.ok(validateManifest({ version: "1.0.0", skills: [entry()] }, () => null).some((e) => e.includes("不存在")));
  assert.ok(validateManifest({ version: "1.0.0", skills: [entry({ type: "skill" })] }, read).some((e) => e.includes("frontmatter")));
});
