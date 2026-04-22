# Silent Label Print — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the blocking "Étiquette envoyée à l'imprimante" OK dialog so label printing goes straight to the Dymo without the user clicking OK every time.

**Architecture:** The OK dialog is not a Windows/Dymo prompt — it's our own `tkinter.messagebox.showinfo` call fired after `DymoPrinter.print_label_pdf()` returns. The fix is to delete the two success popups (single print at `main_window.py:906`, batch print at `main_window.py:1027-1028`). Error popups stay — they still need acknowledgement. SumatraPDF already prints silently in the background, so the user simply sees the label roll out of the Dymo with no UI friction.

**Tech Stack:** Python 3.x · CustomTkinter · tkinter.messagebox · PyInstaller · GitHub Actions (builds the `.exe` on push to `main`).

---

## File Structure

| File | Change |
|------|--------|
| `ui/main_window.py` | Remove success `messagebox.showinfo` in `_print_label` (line 906) and `_batch_print_labels` (lines 1027-1028). Keep all error popups. |

No new files. No tests added — `ui/main_window.py` has no existing test coverage (CustomTkinter UI is not currently under test), so verification is manual via `python app.py` locally and the rebuilt `.exe` on the customer's Windows PC.

---

### Task 1: Remove single-label success popup

**Files:**
- Modify: `ui/main_window.py:906`

- [ ] **Step 1: Locate the exact block**

Open [ui/main_window.py](ui/main_window.py) and find the `_print_label` method around line 876. The current tail of the `try` block reads:

```python
        try:
            PdfGenerator.generate_label(
                self._selected_product, tmp_path, logo,
                width_mm=size["width_mm"],
                height_mm=size["height_mm"])
            DymoPrinter.print_label_pdf(tmp_path, printer_name=name)
            self._history.add(self._selected_product, fmt="label")
            self._refresh_history()
            messagebox.showinfo("Succès", "Étiquette envoyée à l'imprimante.")
        except Exception as e:
            messagebox.showerror("Erreur impression", str(e))
```

- [ ] **Step 2: Delete the success popup line**

Replace the block with:

```python
        try:
            PdfGenerator.generate_label(
                self._selected_product, tmp_path, logo,
                width_mm=size["width_mm"],
                height_mm=size["height_mm"])
            DymoPrinter.print_label_pdf(tmp_path, printer_name=name)
            self._history.add(self._selected_product, fmt="label")
            self._refresh_history()
        except Exception as e:
            messagebox.showerror("Erreur impression", str(e))
```

The error branch stays intact — users must still see print failures.

- [ ] **Step 3: Verify the file parses**

Run:

```bash
cd /Users/pc/CandyStock && python -c "import ast; ast.parse(open('ui/main_window.py').read())"
```

Expected: no output, exit code 0. Any `SyntaxError` means the edit broke indentation — re-read the block and fix.

---

### Task 2: Remove batch-label success popup

**Files:**
- Modify: `ui/main_window.py:1024-1028`

- [ ] **Step 1: Locate the batch tail**

In the `_batch_print_labels` method around line 990, the current tail after the for-loop reads:

```python
        self._refresh_history()
        if errors:
            messagebox.showerror("Erreurs", "\n".join(errors))
        else:
            messagebox.showinfo("Succès",
                f"{len(products)} étiquette(s) envoyée(s) à l'imprimante.")
```

- [ ] **Step 2: Drop the else-branch popup**

Replace with:

```python
        self._refresh_history()
        if errors:
            messagebox.showerror("Erreurs", "\n".join(errors))
```

Errors still surface. Success is silent — user sees N labels coming out of the Dymo, which is the actual feedback.

- [ ] **Step 3: Verify the file parses**

Run:

```bash
cd /Users/pc/CandyStock && python -c "import ast; ast.parse(open('ui/main_window.py').read())"
```

Expected: no output, exit code 0.

---

### Task 3: Local smoke test on macOS

**Files:** none modified — verification only.

- [ ] **Step 1: Launch the app**

Run:

```bash
cd /Users/pc/CandyStock && python app.py
```

Expected: main window opens, no tracebacks in the console.

- [ ] **Step 2: Trigger a label print**

Load any Excel from the repo root (e.g. `sales-by-product.xlsx`), select one row, click the single-label Print button.

Expected: **no popup appears**. Label is sent to the configured printer (or a harmless `lp` CUPS call on macOS). The app stays interactive — no modal to dismiss.

- [ ] **Step 3: Trigger a batch print**

Check 2-3 rows, click batch-label Print.

Expected: **no success popup**. If the test printer is unreachable, the error popup should still fire — confirm that error path is untouched.

- [ ] **Step 4: Run the existing test suite**

Run:

```bash
cd /Users/pc/CandyStock && python -m pytest tests/ -q
```

Expected: all tests pass. None of them exercise `main_window.py`, so the result should match what it was before the edit — a green baseline proves nothing imported-time broke.

---

### Task 4: Commit and push so GitHub Actions rebuilds the .exe

**Files:** none modified — git action only.

- [ ] **Step 1: Stage and commit**

Run:

```bash
cd /Users/pc/CandyStock && git add ui/main_window.py docs/superpowers/plans/2026-04-22-silent-label-print.md && git commit -m "fix: remove OK popup after label print — send straight to Dymo"
```

Expected: one commit created on `main`.

- [ ] **Step 2: Push to trigger the Windows EXE workflow**

Run:

```bash
cd /Users/pc/CandyStock && git push origin main
```

Expected: remote accepts the push. The push to `main` with changes under `ui/**` matches the workflow's path filter per `CLAUDE.md`, so the GitHub Actions "Build Windows EXE" job starts automatically.

- [ ] **Step 3: Verify the build is running**

Run:

```bash
cd /Users/pc/CandyStock && gh run list --workflow "Build Windows EXE" --limit 1
```

Expected: a single row with status `queued` or `in_progress`. If status is `failed`, run `gh run view --log-failed` and fix before telling the customer to re-download.

- [ ] **Step 4: Wait for the release to refresh**

Run:

```bash
cd /Users/pc/CandyStock && gh run watch
```

Expected: watches until completion, exits 0 on success. Then confirm the `latest` release updated:

```bash
cd /Users/pc/CandyStock && gh release view latest --json publishedAt,assets -q '.publishedAt, .assets[].name'
```

Expected: `publishedAt` is within the last few minutes; assets contain `CandyStock.exe` (or equivalent).

---

### Task 5: Customer verification

**Files:** none — customer action.

- [ ] **Step 1: Tell the customer to re-download**

Send the customer the GitHub releases URL (`latest` tag) and ask them to download the new `.exe` and overwrite the previous one.

- [ ] **Step 2: Confirm with them that the OK popup is gone**

Ask for a yes/no: when they click Print on a label, does the popup still appear? If yes, their `.exe` is still the old cached build — have them check the version indicator in the window title and re-download. If no, ticket closed.

---

## Self-Review

**Spec coverage.** User reported: "a window opens when sending to print labels — wants to send straight without pushing OK every time." Single-label path (Task 1) and batch-label path (Task 2) are both addressed. A4 poster print uses a different code path (`open_pdf_and_print`) which intentionally opens the system print dialog and is out of scope per the user's wording ("labels").

**Placeholder scan.** No TBDs, no "add error handling", no "similar to Task N". Every code step shows full replacement blocks with surrounding context so the engineer can locate and replace without ambiguity.

**Type consistency.** No new symbols introduced. The only touched identifier is the built-in `messagebox.showinfo` — removed, not renamed. `messagebox.showerror` calls in the same functions remain unchanged.

**Known non-issue.** `tests/test_printer.py:32-36` is already out of sync with `src/printer.py` (it asserts `lp -d <name> <pdf>` but the code passes extra `-o` options). Pre-existing; unrelated to this plan; do not touch it here.
