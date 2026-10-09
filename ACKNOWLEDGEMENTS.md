# Acknowledgements — clock-fred-tamlinux

Researched 2026-10-09. Thank you to the people whose software, designs, maintenance, testing and public reports make this work possible.

Names are ordered alphabetically by the displayed public name (case and accents ignored for sorting). A self-published profile name is used when available; otherwise the public handle or name in an upstream credit is retained. No private identities, locations, phone numbers or commit-email harvesting are included. Affiliations below are self-reported public profile fields or explicitly attributed project roles; they are not independently verified employment records. Contact links and emails are only those publicly offered by the person or their project.

Tamlinux additions are distributed under GPL-3.0-or-later; see [LICENSE](LICENSE). Upstream works retain their own terms. Copyright notices are attributed to works and their stated holders, not inferred from contributor counts. The Free Software Foundation copyright on a GPL/LGPL license document is not treated as ownership of the software. These thanks supplement, and do not replace, required license and source notices.

[UPSTREAM.md](UPSTREAM.md) records this repository’s code ancestry and design references. A runtime dependency, design inspiration, bug report and copied component are different contributions; the entries say which connection is established.

Omarchy component authors were checked against the public history through v4.0.4. Older clones are recorded in UPSTREAM.md; attribution to that component’s history does not mean every later change was copied into this plugin. Runtime and font credits identify upstream foundations, not co-authorship of Fred’s additions.

Each named entry identifies an authored component, a documented design influence, a specific change or public report, or responsibility for a foundation used by this repository. Contributor-roster membership alone is not enough for a named entry. Wider communities are credited collectively below.

**Version scope:** Hyprland credits describe the temporary Tamlinux 0.x platform and its compatibility patches. Tamlinux’s [public roadmap](https://github.com/greenermoose/tamlinux/blob/main/README.md) removes Hyprland at 1.0 in favor of Sway. Remove these dependency-only entries from future acknowledgements when the stack is no longer used. Historical forks and any retained derived code keep their applicable source notices.

## People

| Public name and brief background / contribution | Public affiliation and contact |
| --- | --- |
| **Dave Gandy (`davegandy`)** — Creator of Font Awesome. Its icon-font designs supply recognizable symbols, including the weather sun. [Work, license and copyright](#font-awesome). [Evidence](https://fontawesome.com/v4/license/) | No affiliation stated in the inspected public profile/credit. [Public profile / project contact](https://github.com/davegandy); [Public email](mailto:dave@davegandy.com) |
| **David Heinemeier Hansson (`dhh`)** — Creator of Omarchy. Its shell, UI conventions and plugin host form the current base and the documented ancestry of several fred.* components. [Work, license and copyright](#omarchy). [Evidence 1](https://github.com/omacom/omarchy) [Evidence 2](https://github.com/omacom/omawrite) [Evidence 3](https://github.com/omacom/omarchy/commit/b83505d7380bbe0525f56f5dc556c103848d34d5) | 37signals [Public profile / project contact](https://github.com/dhh); [Website](https://dhh.dk); [Public email](mailto:dhh@hey.com) |
| **Fred Horch (`greenermoose`)** — Tamlinux creator and maintainer. Directed this repository’s design, implementation, testing and upstream integration, including the separately documented AI-assisted work. [Evidence](https://github.com/greenermoose/tamlinux) | No affiliation stated in the inspected public profile/credit. [Public profile / project contact](https://github.com/greenermoose) |
| **Guido van Rossum (`gvanrossum`)** — Creator of Python, the interpreter and standard library used by the suite’s command and data helpers. [Work, license and copyright](#python). [Evidence](https://www.python.org/doc/essays/foreword/) | Microsoft [Public profile / project contact](https://github.com/gvanrossum); [Website](https://python.org/~guido/) |
| **HANCORE (`HANCORE-linux`)** — Marketplace maintainer and named public reviewer. Feedback on subprocess supervision, bounded calendar input and safe cache writes shaped the clock’s hardening and shared suite patterns. [Work, license and copyright](#marketplace). [Evidence](https://github.com/omacom/omarchy-plugin-marketplace/issues/6509#issuecomment-5647408125) | No affiliation stated in the inspected public profile/credit. [Public profile / project contact](https://github.com/HANCORE-linux) |
| **Konstantin Bulenkov (`bulenkov`)** — JetBrains Mono project lead; helped make the base typeface used by the installed Nerd Font available. [Work, license and copyright](#jetbrains-mono). [Evidence](https://www.jetbrains.com/lp/mono/) | @JetBrains [Public profile / project contact](https://github.com/bulenkov); [Website](http://bulenkov.com) |
| **Kristian Høgsberg** — Wayland’s original author and a named copyright holder. Its client/compositor protocol enables both the current shell and the planned Sway desktop. [Work, license and copyright](#wayland). [Evidence](https://github.com/wayland-mirror/wayland/blob/main/COPYING) | Wayland project [Public profile / project contact](https://wayland.freedesktop.org/) |
| **Lars Knoll** — Longtime Qt engineer and Qt chief maintainer at the time of the project’s 2020 technical conference. His engineering leadership helped develop the UI framework used by Quickshell and Omawrite. [Work, license and copyright](#qt). [Evidence](https://www.qt.io/development/resources/videos/foundation-for-the-future-are-we-excited-qt-virtual-tech-con-2020) | Qt project; historical role stated in the 2020 source [Public profile / project contact](https://www.qt.io/development/resources/videos/foundation-for-the-future-are-we-excited-qt-virtual-tech-con-2020) |
| **Linus Torvalds (`torvalds`)** — Creator of Linux. Kernel drivers, /proc and /sys underpin the running workstation and hardware telemetry. [Work, license and copyright](#linux). [Evidence](https://www.kernel.org/) | Linux Foundation [Public profile / project contact](https://github.com/torvalds) |
| **outfoxxed (`outfoxxed`)** — Lead developer of Quickshell, the Qt Quick toolkit that runs the shell, bar widgets, layer surfaces, IPC and helper processes. [Work, license and copyright](#quickshell). [Evidence](https://quickshell.org/) | No affiliation stated in the inspected public profile/credit. [Public profile / project contact](https://github.com/outfoxxed); [Website](https://outfoxxed.me); [Public email](mailto:outfoxxed@outfoxxed.me) |
| **Philipp Nurullin (`PhilippNurullin`)** — Type designer credited by JetBrains for JetBrains Mono, the base face used in JetBrainsMono Nerd Font. [Work, license and copyright](#jetbrains-mono). [Evidence](https://www.jetbrains.com/lp/mono/) | JetBrains Mono project [Public profile / project contact](https://github.com/philippnurullin) |
| **Ryan Hughes (`ryanrhughes`)** — Omarchy shell and plugin-system contributor. The v4.0.4 history records work on widget scaling, theme tokens, built-in plugins and plugin management. [Work, license and copyright](#omarchy). [Evidence 1](https://github.com/omacom/omarchy) [Evidence 2](https://github.com/omacom/omarchy/commit/4f0bdb790b75603a6506daa6603b3576349373d6) [Evidence 3](https://github.com/omacom/omarchy/commit/e8fc2ef08f3aad9f6219b85a8ab8884f27fc953a) | Oodle [Public profile / project contact](https://github.com/ryanrhughes); [Website](https://heyoodle.com); [Public email](mailto:ryan@heyoodle.com) |
| **Ryan L McIntyre (`ryanoasis`)** — Creator of Nerd Fonts. Font patching and collected glyphs provide the installed bar font and icon rendering. [Work, license and copyright](#nerd-fonts). [Evidence](https://github.com/ryanoasis/nerd-fonts) | No affiliation stated in the inspected public profile/credit. [Public profile / project contact](https://github.com/ryanoasis); [Website](https://RyanLMcIntyre.com) |
| **Scott Jones (`scottjones`)** — Added AM/PM format choices to the upstream clock, a useful reference in fred.clock’s component ancestry. [Component commit](https://github.com/omacom/omarchy/commit/72ffd58316265bb770dddfc77983117bf9b91f0a). [Work, license and copyright](#omarchy). [Evidence 1](https://github.com/omacom/omarchy/commit/72ffd58316265bb770dddfc77983117bf9b91f0a) [Evidence 2](https://github.com/omacom/omarchy/commit/7faf53c4c0dcaa8b69bcc496ab1b376a73f75761) [Evidence 3](https://github.com/omacom/omarchy/commit/567e24cd90eb154150614bf5a092fe0e6e7b75e5) | No affiliation stated in the inspected public profile/credit. [Public profile / project contact](https://github.com/scottjones) |
| **Sergey Bugaev (`bugaevc`)** — Author of wl-clipboard, providing the wl-copy command used for panel clipboard actions. [Work, license and copyright](#wl-clipboard). [Evidence](https://github.com/bugaevc/wl-clipboard) | No affiliation stated in the inspected public profile/credit. [Public profile / project contact](https://github.com/bugaevc); [Public email](mailto:bugaevc@gmail.com) |

## Works, licenses and stated copyright notices

The source links below are the authority for complete notices and exceptions. A short notice here is a reference, not a replacement license text. Names in a copyright notice are reproduced as the holder wrote them even when the person now uses a different public display name.

<a id="font-awesome"></a>
### Font Awesome

- **Connection:** Icon glyphs, including the weather sun, provided through the installed font.
- **License:** OFL-1.1 for fonts; MIT for code; CC-BY-4.0 for current SVG/JS icons. [License/source notices](https://github.com/FortAwesome/Font-Awesome/blob/7.x/LICENSE.txt).
- **Stated copyright / limits:** Copyright (c) 2026 Fonticons, Inc.; older installed editions may carry earlier notices. See the license for the edition distributed.
- **Source:** [Upstream project](https://github.com/FortAwesome/Font-Awesome). [Wider contributor community](https://github.com/FortAwesome/Font-Awesome/graphs/contributors).

<a id="hyprland"></a>
### Hyprland

- **Connection:** Temporary compositor for the Tamlinux 0.x transition and source of the compatibility fork. The public roadmap removes Hyprland at 1.0.
- **License:** BSD-3-Clause. [License/source notices](https://github.com/hyprwm/Hyprland/blob/main/LICENSE).
- **Stated copyright / limits:** Copyright (c) 2022-2026, vaxerski
- **Source:** [Upstream project](https://github.com/hyprwm/Hyprland). [Wider contributor community](https://github.com/hyprwm/Hyprland/graphs/contributors).

<a id="jetbrains-mono"></a>
### JetBrains Mono

- **Connection:** Base typeface for the installed JetBrainsMono Nerd Font.
- **License:** OFL-1.1. [License/source notices](https://github.com/JetBrains/JetBrainsMono/blob/master/OFL.txt).
- **Stated copyright / limits:** Copyright 2020 The JetBrains Mono Project Authors (https://github.com/JetBrains/JetBrainsMono); copyright statement(s).
- **Source:** [Upstream project](https://github.com/JetBrains/JetBrainsMono). [Wider contributor community](https://github.com/JetBrains/JetBrainsMono/graphs/contributors).

<a id="linux"></a>
### Linux

- **Connection:** Kernel interfaces and drivers underpin the workstation and telemetry probes.
- **License:** GPL-2.0-only with Linux-syscall-note for relevant UAPI headers; individual files may differ. [License/source notices](https://www.kernel.org/doc/html/latest/process/license-rules.html).
- **Stated copyright / limits:** Many individual and organizational holders; consult each file, not a single blanket ownership claim.
- **Source:** [Upstream project](https://www.kernel.org/doc/html/latest/process/license-rules.html).

<a id="nerd-fonts"></a>
### Nerd Fonts

- **Connection:** Patched system fonts and icon glyph collection used by the bar.
- **License:** MIT for scripts; OFL-1.1 and other source-font licenses for font assets. [License/source notices](https://github.com/ryanoasis/nerd-fonts/blob/master/LICENSE).
- **Stated copyright / limits:** Copyright (c) 2014 Ryan L McIntyre; constituent fonts retain their own notices.
- **Source:** [Upstream project](https://github.com/ryanoasis/nerd-fonts). [Wider contributor community](https://github.com/ryanoasis/nerd-fonts/graphs/contributors).

<a id="omarchy"></a>
### Omarchy

- **Connection:** Current Tamlinux 0.x base, shell/plugin integration, and documented cloned components.
- **License:** MIT. [License/source notices](https://github.com/omacom/omarchy/blob/quattro/LICENSE).
- **Stated copyright / limits:** Copyright (c) David Heinemeier Hansson
- **Source:** [Upstream project](https://github.com/omacom/omarchy). [Wider contributor community](https://github.com/omacom/omarchy/graphs/contributors).

<a id="marketplace"></a>
### Omarchy Plugin Marketplace

- **Connection:** Plugin registry, distribution discovery and public security review.
- **License:** MIT. [License/source notices](https://github.com/omacom/omarchy-plugin-marketplace/blob/main/LICENSE).
- **Stated copyright / limits:** Copyright (c) 2026 HANCORE
- **Source:** [Upstream project](https://github.com/omacom/omarchy-plugin-marketplace). [Wider contributor community](https://github.com/omacom/omarchy-plugin-marketplace/graphs/contributors).

<a id="python"></a>
### Python

- **Connection:** Interpreter and standard library used by the Tamlinux helper programs.
- **License:** PSF License Version 2 and historical bundled notices. [License/source notices](https://docs.python.org/3/license.html).
- **Stated copyright / limits:** Python Software Foundation and the historical holders recorded in the license.
- **Source:** [Upstream project](https://docs.python.org/3/license.html).

<a id="qt"></a>
### Qt / Qt Quick

- **Connection:** UI, QML, controls and graphics foundations used by the shell and Omawrite.
- **License:** Qt module-specific LGPL/GPL or commercial terms; see installed module licenses. [License/source notices](https://www.qt.io/licensing/open-source-lgpl-obligations).
- **Stated copyright / limits:** The Qt Company and many other contributors; module source files retain their notices.
- **Source:** [Upstream project](https://www.qt.io/licensing/open-source-lgpl-obligations).

<a id="quickshell"></a>
### Quickshell

- **Connection:** Runtime for the QML shell and fred.* widgets.
- **License:** LGPL-3.0; consult file SPDX headers for applicable terms. [License/source notices](https://github.com/quickshell-mirror/quickshell/blob/master/LICENSE).
- **Stated copyright / limits:** No project-specific holder established from the inspected license text; see source notices. The license-text author is not assumed to own the software.
- **Source:** [Upstream project](https://github.com/quickshell-mirror/quickshell). [Wider contributor community](https://github.com/quickshell-mirror/quickshell/graphs/contributors).

<a id="wayland"></a>
### Wayland

- **Connection:** Display protocol used by the current desktop and the planned Sway desktop; a foundation independent of Hyprland.
- **License:** MIT-style license; consult individual file notices. [License/source notices](https://github.com/wayland-mirror/wayland/blob/main/COPYING).
- **Stated copyright / limits:** Copyright © 2008-2012 Kristian Høgsberg; Copyright © 2010-2012 Intel Corporation; Copyright © 2011 Benjamin Franzke; Copyright © 2012 Collabora, Ltd.
- **Source:** [Upstream project](https://wayland.freedesktop.org/). [Wider contributor community](https://github.com/wayland-mirror/wayland/graphs/contributors).

<a id="wl-clipboard"></a>
### wl-clipboard

- **Connection:** wl-copy provides clipboard operations for panels.
- **License:** GPL-3.0; see upstream notices. [License/source notices](https://github.com/bugaevc/wl-clipboard/blob/master/COPYING).
- **Stated copyright / limits:** No project-specific holder established from the inspected license text; see source notices. The license-text author is not assumed to own the software.
- **Source:** [Upstream project](https://github.com/bugaevc/wl-clipboard). [Wider contributor community](https://github.com/bugaevc/wl-clipboard/graphs/contributors).

## Community credit and coverage

We also thank the wider upstream communities: reviewers, translators, documentation writers, package maintainers, testers, issue reporters and accessibility contributors. The project/community links above recognize their wider work. This researched list emphasizes identifiable connections to this repository; it is not a complete census of every transitive dependency or a claim of endorsement. Public profiles and affiliations can change; the date above identifies this review.

The [Qt contributors](https://code.qt.io/), [Wayland contributors](https://gitlab.freedesktop.org/wayland/wayland), [Arch package maintainers](https://archlinux.org/people/) and their dependency communities provide additional foundations. Their licenses and copyright notices remain in the individual upstream projects and installed packages; no blanket ownership or single license is assigned to those communities.

The broader alphabetical list for the public Tamlinux ecosystem, including design, data, typeface, toolchain and planned-base contributions, is in [Tamlinux’s acknowledgements](https://github.com/greenermoose/tamlinux/blob/main/ACKNOWLEDGEMENTS.md).

To correct a name, attribution, affiliation or contact preference, please open an issue in this repository or contact [Fred’s public account](https://github.com/greenermoose). Only evidence-backed additions should be made; do not infer identities behind pseudonyms.

Research and compilation were AI-assisted by Codex under Fred’s direction. AI systems and provider organizations are not listed as humans; existing AI provenance records, where present, describe their separate role.
