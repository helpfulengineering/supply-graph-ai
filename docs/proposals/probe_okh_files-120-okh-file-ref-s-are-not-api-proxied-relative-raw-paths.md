# Proposal: 120 OKH file ref(s) are not API-proxied (relative/raw paths)

Status: **draft — awaiting human review**  
Probe: `probe_okh_files`  
Kind: `gap` / `error`  
Generated: 2026-07-08

## Problem (probe evidence)

120 OKH file ref(s) are not API-proxied (relative/raw paths)

```json
{
  "samples": [
    {
      "path": "OSHW_mark_US000236.png",
      "reachable": false,
      "status": 0,
      "reason": "relative_path_no_api_proxy",
      "kind": "gap",
      "title": "OSHW_mark_US000236.png",
      "field": "design_files"
    },
    {
      "path": "BBB_SCH.pdf",
      "reachable": false,
      "status": 0,
      "reason": "relative_path_no_api_proxy",
      "kind": "gap",
      "title": "BBB_SCH.pdf",
      "field": "design_files"
    },
    {
      "path": "BBB_SRM.pdf",
      "reachable": false,
      "status": 0,
      "reason": "relative_path_no_api_proxy",
      "kind": "gap",
      "title": "BBB_SRM.pdf",
      "field": "design_files"
    },
    {
      "path": "images/image77.jpg",
      "reachable": false,
      "status": 0,
      "reason": "relative_path_no_api_proxy",
      "kind": "gap",
      "title": "image77.jpg",
      "field": "design_files"
    },
    {
      "path": "images/image88.jpg",
      "reachable": false,
      "status": 0,
      "reason": "relative_path_no_api_proxy",
      "kind": "gap",
      "title": "image88.jpg",
      "field": "design_files"
    },
    {
      "path": "images/image89.jpg",
      "reachable": false,
      "status": 0,
      "reason": "relative_path_no_api_proxy",
      "kind": "gap",
      "title": "image89.jpg",
      "field": "design_files"
    },
    {
      "path": "images/image60.png",
      "reachable": false,
      "status": 0,
      "reason": "relative_path_no_api_proxy",
      "kind": "gap",
      "title": "image60.png",
      "field": "design_files"
    },
    {
      "path": "images/image48.png",
      "reachable": false,
      "status": 0,
      "reason": "relative_path_no_api_proxy",
      "kind": "gap",
      "title": "image48.png",
      "field": "design_files"
    },
    {
      "path": "images/image75.jpg",
      "reachable": false,
      "status": 0,
      "reason": "relative_path_no_api_proxy",
      "kind": "gap",
      "title": "image75.jpg",
      "field": "design_files"
    },
    {
      "path": "images/image49.png",
      "reachable": false,
      "status": 0,
      "reason": "relative_path_no_api_proxy",
      "kind": "gap",
      "title": "image49.png",
      "field": "design_files"
    },
    {
      "path": "images/image8.jpg",
      "reachable": false,
      "status": 0,
      "reason": "relative_path_no_api_proxy",
      "kind": "gap",
      "title": "image8.jpg",
      "field": "design_files"
    },
    {
      "path": "images/image59.png",
      "reachable": false,
      "status": 0,
      "reason": "relative_path_no_api_proxy",
      "kind": "gap",
      "title": "image59.png",
      "field": "design_files"
    },
    {
      "path": "images/image65.png",
      "reachable": false,
      "status": 0,
      "reason": "relative_path_no_api_proxy",
      "kind": "gap",
      "title": "image65.png",
      "field": "design_files"
    },
    {
      "path": "images/image71.jpg",
      "reachable": false,
      "status": 0,
      "reason": "relative_path_no_api_proxy",
      "kind": "gap",
      "title": "image71.jpg",
      "field": "design_files"
    },
    {
      "path": "images/image64.png",
      "reachable": false,
      "status": 0,
      "reason": "relative_path_no_api_proxy",
      "kind": "gap",
      "title": "image64.png",
      "field": "design_files"
    },
    {
      "path": "images/image58.png",
      "reachable": false,
      "status": 0,
      "reason": "relative_path_no_api_proxy",
      "kind": "gap",
      "title": "image58.png",
      "field": "design_files"
    },
    {
      "path": "images/image9.jpg",
      "reachable": false,
      "status": 0,
      "reason": "relative_path_no_api_proxy",
      "kind": "gap",
      "title": "image9.jpg",
      "field": "design_files"
    },
    {
      "path": "images/image66.png",
      "reachable": false,
      "status": 0,
      "reason": "relative_path_no_api_proxy",
      "kind": "gap",
      "title": "image66.png",
      "field": "design_files"
    },
    {
      "path": "images/image73.jpg",
      "reachable": false,
      "status": 0,
      "reason": "relative_path_no_api_proxy",
      "kind": "gap",
      "title": "image73.jpg",
      "field": "design_files"
    },
    {
      "path": "images/image67.png",
      "reachable": false,
      "status": 0,
      "reason": "relative_path_no_api_proxy",
      "kind": "gap",
      "title": "image67.png",
      "field": "design_files"
    }
  ],
  "recommendation": "Add OHM storage/file API (signed URLs or /api/okh/{id}/files/...) and update OkhFileGroup to use download + in-browser viewer by MIME type (pdf, png, stl, md)."
}
```

## Proposed fix (to be refined)

Add OHM storage/file API (signed URLs or /api/okh/{id}/files/...) and update OkhFileGroup to use download + in-browser viewer by MIME type (pdf, png, stl, md).

## Scope

- [ ] Architecture / infrastructure
- [ ] Backend API
- [ ] Frontend UI
- [ ] Configuration / deployment (Azure Container Apps)

## Acceptance criteria

- [ ] Probe `probe_okh_files` passes against staging
- [ ] Regression test or synthetic journey covers the fixed path
- [ ] Operator doc updated if runbooks change

## Review checklist

- [ ] Root cause confirmed (not just symptom)
- [ ] Fix approach agreed
- [ ] Rollout / rollback plan noted
- [ ] Ready for implementation issue

---
*Auto-generated by OHM triage harness. Edit before approving.*
