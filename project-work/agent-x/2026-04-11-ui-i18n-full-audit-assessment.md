# 2026-04-11 UI i18n Full Audit Assessment

## Problem Statement

The current system still contains a large number of visible Chinese-locale display issues, including but not limited to:

- raw i18n keys rendered directly in the UI
- garbled/mojibake Chinese text
- untranslated English labels in Chinese workflows
- missing locale-backed labels in dropdowns, tooltips, modals, and settings forms

The example already confirmed in the current build includes dataset-settings UI showing strings such as:

- `knowledgeDetails.enableChildrenDelimiter`
- `knowledgeConfiguration.tocExtraction`
- `knowledgeConfiguration.overlappedPercent`

This indicates the issue is not isolated to one page.

## Scope Judgment

This must be treated as a full-surface UI audit and remediation, not a single-point fix.

The assignee must inspect:

1. every main page
2. every settings page
3. every admin page
4. every dropdown menu
5. every modal/dialog
6. every tooltip/help text
7. critical create/edit/detail forms

## Why A Full Audit Is Required

The current defect pattern suggests multiple classes of problems co-exist:

- missing `zh` locale keys
- wrong locale key references in components
- fallback strings not localized
- encoded/garbled source literals
- old upstream UI paths merged with incomplete project-specific locale updates

If only the currently visible page is patched, the system will still ship with many unrepaired user-visible defects.

## Required Delivery Standard

The remediation ticket must require:

- browser-based traversal of every reachable page
- Chinese locale as the primary validation target
- explicit coverage of dropdowns and modal dialogs
- a completion record with a checked page-by-page inventory

## Assignee Recommendation

This is a focused remediation ticket, so it should be assigned to a numbered specialist agent:

- `agent-004`
