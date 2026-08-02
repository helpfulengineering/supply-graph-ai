import { describe, expect, it } from "vitest";
import { checkRepoUrl, parseRepoUrlList } from "./urlValidation";

describe("checkRepoUrl", () => {
  it("accepts a github repo and normalises it", () => {
    const r = checkRepoUrl("https://github.com/nasa-jpl/open-source-rover");
    expect(r.valid).toBe(true);
    expect(r.normalized).toBe("https://github.com/nasa-jpl/open-source-rover");
  });

  it("accepts gitlab", () => {
    expect(checkRepoUrl("https://gitlab.com/owner/project").valid).toBe(true);
  });

  it("strips a trailing .git, deep paths, query and fragment", () => {
    expect(checkRepoUrl("https://github.com/a/b.git").normalized).toBe(
      "https://github.com/a/b",
    );
    expect(checkRepoUrl("https://github.com/a/b/tree/main/docs?x=1#y").normalized).toBe(
      "https://github.com/a/b",
    );
  });

  it("ignores a www prefix and surrounding whitespace", () => {
    expect(checkRepoUrl("  https://www.github.com/a/b  ").normalized).toBe(
      "https://github.com/a/b",
    );
  });

  it("rejects empty input", () => {
    expect(checkRepoUrl("   ").problem).toBe("empty");
  });

  it("rejects non-URLs", () => {
    expect(checkRepoUrl("not a url").problem).toBe("not_a_url");
  });

  it("rejects unsupported hosts", () => {
    expect(checkRepoUrl("https://bitbucket.org/a/b").problem).toBe("unsupported_host");
  });

  it("rejects a host with no repository path", () => {
    expect(checkRepoUrl("https://github.com/owner").problem).toBe("missing_repo_path");
  });

  it("rejects non-http schemes, including git@ style remotes", () => {
    expect(checkRepoUrl("ftp://github.com/a/b").problem).toBe("not_http");
    // SSH remotes are a common paste; they must not silently pass.
    expect(checkRepoUrl("git@github.com:a/b.git").valid).toBe(false);
  });

  it("always supplies a message when invalid", () => {
    for (const bad of ["", "nope", "https://example.com/a/b", "https://github.com/x"]) {
      const r = checkRepoUrl(bad);
      expect(r.valid).toBe(false);
      expect(r.message && r.message.length).toBeGreaterThan(0);
    }
  });
});

describe("parseRepoUrlList", () => {
  it("accepts a single URL", () => {
    const r = parseRepoUrlList("https://github.com/a/b");
    expect(r.valid).toBe(true);
    expect(r.urls).toEqual(["https://github.com/a/b"]);
  });

  it("splits on commas, trims, and deduplicates", () => {
    const r = parseRepoUrlList(
      "https://github.com/a/one, https://github.com/b/two, https://github.com/a/one.git",
    );
    expect(r.valid).toBe(true);
    expect(r.urls).toEqual([
      "https://github.com/a/one",
      "https://github.com/b/two",
    ]);
  });

  it("rejects the whole list when any entry is invalid", () => {
    const r = parseRepoUrlList(
      "https://github.com/a/one, https://bitbucket.org/a/b",
    );
    expect(r.valid).toBe(false);
    expect(r.message).toMatch(/github and gitlab/i);
    expect(r.urls).toEqual(["https://github.com/a/one"]);
  });

  it("rejects empty input", () => {
    expect(parseRepoUrlList("  ,  ").valid).toBe(false);
  });
});
