# #561: a first-time designer adds an electronics design

[#561](https://github.com/helpfulengineering/supply-graph-ai/issues/561) is a
first-contact report from the developer of Frugal-IoT, who tried to add
[`mitra42/frugal-iot-hw-sensor`](https://github.com/mitra42/frugal-iot-hw-sensor)
on openhardwaremanager.org. Each problem they hit is an acceptance test, marked
as an expected failure naming the sub-issue that fixes it:

| What they hit | Test | Fixed by |
|---|---|---|
| The landing page is only about finding designs | e2e: offers adding a design | #567 |
| The LLM error didn't say to register | e2e: says to register, in plain words | #565 |
| A removed process was still in the YAML | e2e: removed process gone from YAML; backend: gone from every place it was stored | #562 |
| `SCHEMATIC.pdf` defaulted to design_files at 0.3 | backend: schematic is recognised | #563 |
| "Sheet metal forming" on a PCB | backend: no sheet metal process | #564 |
| Invented version 0.2.4 | backend: a version is never invented | #564 |
| BOM had no file, no link, no components | backend: links the BOM file; lists the components | #564 |
| "Not sure what is supposed to go here" (BOM) | e2e: says what the BOM is | #564 |
| Generate could only download | e2e: a signed-in designer saves | #566 |
| Registered, then started over | e2e: offered sign-in to save, keeps edits | #572 |
| "I'm going to lose those three keys" | e2e: one thing to keep; signs in with a password | #571, #570 |

- Backend: `tests/integration/test_issue_561_first_contact.py`, run against
  `stand_in.py`, which reproduces the repository's file layout. The repository
  has no licence, so none of its content is copied.
- Frontend: `frontend/e2e/issue-561.spec.ts`, on the mocked API.

A fix PR removes its tests' markers. When neither file has a marker left, every
problem is fixed.

```bash
uv run pytest tests/integration/test_issue_561_first_contact.py -rxX
cd frontend && npx playwright test e2e/issue-561.spec.ts --project=mocked
```

## Replaying the report by hand

Do this on a local node, then on openhardwaremanager.org once a release with
the fixes is deployed. Start signed out, in a fresh private window.

1. **Landing page.** There is an "Add your design" action next to finding
   designs. It leads to Generate. (#567)
2. **For designers page.** The docs explain that a designer becomes a member of
   a node and installs nothing; running a node is for organisations. (#567)
3. **Generate, signed out, with the LLM.** Paste
   `https://github.com/mitra42/frugal-iot-hw-sensor`. The message says
   generating with the LLM needs an account here, links to register and sign
   in, and offers to continue without the LLM. No `Authorization: Bearer` text.
   (#565)
4. **Sign up from that message.** A short form opens in place: username,
   password, display name. Afterwards you are signed in, still on Generate, with
   the URL still filled in. (#572, #570)
5. **What signup asks you to keep.** One recovery code, with copy and download,
   and a checkbox to confirm you saved it. No API token and no "key pair". (#571)
6. **Generate with the LLM.** Check the result:
   - Version is blank, with a warning that no release, tag or version file
     was found and that file names mention v02. Never 0.2.4 or 1.0.0. (#564)
   - Manufacturing processes include PCB Fabrication and no Sheet Metal
     Forming. (#564)
   - The BOM names `BOM.csv` (or the JLCPCB file), lists its parts, and the
     editor says what a BOM is. (#564)
   - `SCHEMATIC.pdf` is categorised as the schematic, not "defaulting to
     design_files". (#563)
7. **Edit, then download.** Enter version 0.2. Remove a process, download YAML,
   and search the file: the process is in none of `manufacturing_processes`,
   `manufacturing_specs.process_requirements` or `tsdc`. (#562)
8. **Save to this node.** You land on the design's page. It is private,
   attributed to you, and the generation details can be reopened. (#566)
9. **Sign out, then back in** with username and password, in a new window. The
   design is listed on your account page. (#570)

Steps 3 and 6 need a node with an LLM provider configured. Without one,
generation runs without the LLM and step 3 does not apply.
