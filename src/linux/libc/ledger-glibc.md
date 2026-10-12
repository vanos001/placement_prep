# glibc API Coverage Ledger

## Overview

This ledger inventories the glibc public API in two layers that are kept
deliberately separate:

1. **Documented API** — functions documented in the glibc manual (manual
   version: glibc master `manual/*.texi`, fetched from the source mirror).
   The *Family* column is the manual's own `@chapter` title, so the family
   taxonomy comes from the manual itself rather than an invented scheme.
2. **Exported symbols** — dynamic symbols in the installed glibc 2.41
   (`nm -D --with-symbol-versions` on `libc.so.6`, `libm.so.6`,
   `libresolv.so.2`, and the post-2.34 compatibility stubs). `GLIBC_PRIVATE`
   symbols and internal `__`-prefixed aliases are excluded from rows but
   counted in the totals; they are ABI surface but not supported API.

The *Header* column comes from the man-pages project (`man3/<name>.3`,
HEADERS block) and names the canonical `#include` for the documented entry
point. The *Exported* column records the newest `GLIBC_2.x` symbol version
carrying the name (glibc 2.41 on Debian trixie), which is the ABI
compatibility level, not the year the function was added to the manual.

**Status vocabulary** (defined in the [encyclopedia overview](../interface-encyclopedia.md)):
`not-started` → inventoried only · `researched` → sources read ·
`documented` → full entry (declaration, semantics, return/errors, thread
safety, portability, example, references) · `source-limited` → documented
with fewer sources than the standard.

## Ledger (documented API, by manual chapter)

### Arithmetic Functions

| ID | Function | Header | Exported | Status | Chapter | Notes |
|---|---|---|---|---|---|---|
| GLIBC-abs | abs | `stdlib.h` | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-atof | atof | `stdlib.h` | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-atoi | atoi | `stdlib.h` | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-atol | atol | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-atoll | atoll | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-cabs | cabs | `complex.h` | — | documented | [glibc catalog](./overview.md) | —complex; complex |
| GLIBC-cabsf | cabsf | — | — | documented | [glibc catalog](./overview.md) | —complex; complex |
| GLIBC-cabsfN | cabsfN | — | — | documented | [glibc catalog](./overview.md) | —complex; complex |
| GLIBC-cabsfNx | cabsfNx | — | — | documented | [glibc catalog](./overview.md) | —complex; complex |
| GLIBC-cabsl | cabsl | — | — | documented | [glibc catalog](./overview.md) | —complex; complex |
| GLIBC-canonicalize | canonicalize | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-canonicalizef | canonicalizef | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-canonicalizefN | canonicalizefN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-canonicalizefNx | canonicalizefNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-canonicalizel | canonicalizel | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-carg | carg | `complex.h` | — | documented | [glibc catalog](./overview.md) | —complex; complex |
| GLIBC-cargf | cargf | — | — | documented | [glibc catalog](./overview.md) | —complex; complex |
| GLIBC-cargfN | cargfN | — | — | documented | [glibc catalog](./overview.md) | —complex; complex |
| GLIBC-cargfNx | cargfNx | — | — | documented | [glibc catalog](./overview.md) | —complex; complex |
| GLIBC-cargl | cargl | — | — | documented | [glibc catalog](./overview.md) | —complex; complex |
| GLIBC-ceil | ceil | `math.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-ceilf | ceilf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-ceilfN | ceilfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-ceilfNx | ceilfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-ceill | ceill | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-cimag | cimag | `complex.h` | — | documented | [glibc catalog](./overview.md) | —complex; complex |
| GLIBC-cimagf | cimagf | — | — | documented | [glibc catalog](./overview.md) | —complex; complex |
| GLIBC-cimagfN | cimagfN | — | — | documented | [glibc catalog](./overview.md) | —complex; complex |
| GLIBC-cimagfNx | cimagfNx | — | — | documented | [glibc catalog](./overview.md) | —complex; complex |
| GLIBC-cimagl | cimagl | — | — | documented | [glibc catalog](./overview.md) | —complex; complex |
| GLIBC-conj | conj | `complex.h` | — | documented | [glibc catalog](./overview.md) | —complex; complex |
| GLIBC-conjf | conjf | — | — | documented | [glibc catalog](./overview.md) | —complex; complex |
| GLIBC-conjfN | conjfN | — | — | documented | [glibc catalog](./overview.md) | —complex; complex |
| GLIBC-conjfNx | conjfNx | — | — | documented | [glibc catalog](./overview.md) | —complex; complex |
| GLIBC-conjl | conjl | — | — | documented | [glibc catalog](./overview.md) | —complex; complex |
| GLIBC-copysign | copysign | `math.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-copysignf | copysignf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-copysignfN | copysignfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-copysignfNx | copysignfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-copysignl | copysignl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-cproj | cproj | `complex.h` | — | documented | [glibc catalog](./overview.md) | —complex; complex |
| GLIBC-cprojf | cprojf | — | — | documented | [glibc catalog](./overview.md) | —complex; complex |
| GLIBC-cprojfN | cprojfN | — | — | documented | [glibc catalog](./overview.md) | —complex; complex |
| GLIBC-cprojfNx | cprojfNx | — | — | documented | [glibc catalog](./overview.md) | —complex; complex |
| GLIBC-cprojl | cprojl | — | — | documented | [glibc catalog](./overview.md) | —complex; complex |
| GLIBC-creal | creal | `complex.h` | — | documented | [glibc catalog](./overview.md) | —complex; complex |
| GLIBC-crealf | crealf | — | — | documented | [glibc catalog](./overview.md) | —complex; complex |
| GLIBC-crealfN | crealfN | — | — | documented | [glibc catalog](./overview.md) | —complex; complex |
| GLIBC-crealfNx | crealfNx | — | — | documented | [glibc catalog](./overview.md) | —complex; complex |
| GLIBC-creall | creall | — | — | documented | [glibc catalog](./overview.md) | —complex; complex |
| GLIBC-daddl | daddl | — | — | documented | [glibc catalog](./overview.md) | —decimal; decimal |
| GLIBC-ddivl | ddivl | — | — | documented | [glibc catalog](./overview.md) | —decimal; decimal |
| GLIBC-dfmal | dfmal | — | — | documented | [glibc catalog](./overview.md) | —decimal; decimal |
| GLIBC-div | div | `stdlib.h` | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-dmull | dmull | — | — | documented | [glibc catalog](./overview.md) | —decimal; decimal |
| GLIBC-drem | drem | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-dremf | dremf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-dreml | dreml | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-dsqrtl | dsqrtl | — | — | documented | [glibc catalog](./overview.md) | —decimal; decimal |
| GLIBC-dsubl | dsubl | — | — | documented | [glibc catalog](./overview.md) | —decimal; decimal |
| GLIBC-ecvt | ecvt | `stdlib.h` | — | documented | [glibc catalog](./overview.md) | —stdlib; stdlib |
| GLIBC-ecvt_r | ecvt_r | `stdlib.h` | — | documented | [glibc catalog](./overview.md) | —stdlib; stdlib |
| GLIBC-fabs | fabs | `math.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fabsf | fabsf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fabsfN | fabsfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fabsfNx | fabsfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fabsl | fabsl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fadd | fadd | — | — | documented | [glibc catalog](./overview.md) | —decimal; decimal |
| GLIBC-faddl | faddl | — | — | documented | [glibc catalog](./overview.md) | —decimal; decimal |
| GLIBC-fcvt | fcvt | — | — | documented | [glibc catalog](./overview.md) | —stdlib; stdlib |
| GLIBC-fcvt_r | fcvt_r | — | — | documented | [glibc catalog](./overview.md) | —stdlib; stdlib |
| GLIBC-fdim | fdim | `math.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fdimf | fdimf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fdimfN | fdimfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fdimfNx | fdimfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fdiml | fdiml | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fdiv | fdiv | — | — | documented | [glibc catalog](./overview.md) | —decimal; decimal |
| GLIBC-fdivl | fdivl | — | — | documented | [glibc catalog](./overview.md) | —decimal; decimal |
| GLIBC-feclearexcept | feclearexcept | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fedisableexcept | fedisableexcept | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-feenableexcept | feenableexcept | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fegetenv | fegetenv | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fegetexcept | fegetexcept | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fegetexceptflag | fegetexceptflag | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fegetmode | fegetmode | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fegetround | fegetround | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-feholdexcept | feholdexcept | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-feraiseexcept | feraiseexcept | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fesetenv | fesetenv | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fesetexcept | fesetexcept | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fesetexceptflag | fesetexceptflag | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fesetmode | fesetmode | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fesetround | fesetround | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fetestexcept | fetestexcept | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fetestexceptflag | fetestexceptflag | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-feupdateenv | feupdateenv | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-ffma | ffma | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-ffmal | ffmal | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-finite | finite | `math.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-finitef | finitef | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-finitel | finitel | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-floor | floor | `math.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-floorf | floorf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-floorfN | floorfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-floorfNx | floorfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-floorl | floorl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fma | fma | `math.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fMaddfN | fMaddfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fMaddfNx | fMaddfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fmaf | fmaf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fmafN | fmafN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fmafNx | fmafNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fmal | fmal | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fmax | fmax | `math.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fmaxf | fmaxf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fmaxfN | fmaxfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fmaxfNx | fmaxfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fmaximum | fmaximum | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fmaximum_mag | fmaximum_mag | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fmaximum_mag_num | fmaximum_mag_num | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fmaximum_mag_numf | fmaximum_mag_numf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fmaximum_mag_numfN | fmaximum_mag_numfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fmaximum_mag_numfNx | fmaximum_mag_numfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fmaximum_mag_numl | fmaximum_mag_numl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fmaximum_magf | fmaximum_magf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fmaximum_magfN | fmaximum_magfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fmaximum_magfNx | fmaximum_magfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fmaximum_magl | fmaximum_magl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fmaximum_num | fmaximum_num | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fmaximum_numf | fmaximum_numf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fmaximum_numfN | fmaximum_numfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fmaximum_numfNx | fmaximum_numfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fmaximum_numl | fmaximum_numl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fmaximumf | fmaximumf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fmaximumfN | fmaximumfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fmaximumfNx | fmaximumfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fmaximuml | fmaximuml | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fmaxl | fmaxl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fmaxmag | fmaxmag | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fmaxmagf | fmaxmagf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fmaxmagfN | fmaxmagfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fmaxmagfNx | fmaxmagfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fmaxmagl | fmaxmagl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fMdivfN | fMdivfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fMdivfNx | fMdivfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fMfmafN | fMfmafN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fMfmafNx | fMfmafNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fmin | fmin | `math.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fminf | fminf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fminfN | fminfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fminfNx | fminfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fminimum | fminimum | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fminimum_mag | fminimum_mag | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fminimum_mag_num | fminimum_mag_num | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fminimum_mag_numf | fminimum_mag_numf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fminimum_mag_numfN | fminimum_mag_numfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fminimum_mag_numfNx | fminimum_mag_numfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fminimum_mag_numl | fminimum_mag_numl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fminimum_magf | fminimum_magf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fminimum_magfN | fminimum_magfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fminimum_magfNx | fminimum_magfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fminimum_magl | fminimum_magl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fminimum_num | fminimum_num | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fminimum_numf | fminimum_numf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fminimum_numfN | fminimum_numfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fminimum_numfNx | fminimum_numfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fminimum_numl | fminimum_numl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fminimumf | fminimumf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fminimumfN | fminimumfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fminimumfNx | fminimumfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fminimuml | fminimuml | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fminl | fminl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fminmag | fminmag | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fminmagf | fminmagf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fminmagfN | fminmagfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fminmagfNx | fminmagfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fminmagl | fminmagl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fMmulfN | fMmulfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fMmulfNx | fMmulfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fmod | fmod | `math.h` | GLIBC_2.2.5 | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fmodf | fmodf | — | GLIBC_2.2.5 | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fmodfN | fmodfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fmodfNx | fmodfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fmodl | fmodl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fMsqrtfN | fMsqrtfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fMsqrtfNx | fMsqrtfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fMsubfN | fMsubfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fMsubfNx | fMsubfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fmul | fmul | — | — | documented | [glibc catalog](./overview.md) | —decimal; decimal |
| GLIBC-fmull | fmull | — | — | documented | [glibc catalog](./overview.md) | —decimal; decimal |
| GLIBC-fMxaddfN | fMxaddfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fMxaddfNx | fMxaddfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fMxdivfN | fMxdivfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fMxdivfNx | fMxdivfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fMxfmafN | fMxfmafN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fMxfmafNx | fMxfmafNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fMxmulfN | fMxmulfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fMxmulfNx | fMxmulfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fMxsqrtfN | fMxsqrtfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fMxsqrtfNx | fMxsqrtfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fMxsubfN | fMxsubfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fMxsubfNx | fMxsubfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-frexp | frexp | `math.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-frexpf | frexpf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-frexpfN | frexpfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-frexpfNx | frexpfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-frexpl | frexpl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fromfp | fromfp | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fromfpf | fromfpf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fromfpfN | fromfpfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fromfpfNx | fromfpfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fromfpl | fromfpl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fromfpx | fromfpx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fromfpxf | fromfpxf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fromfpxfN | fromfpxfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fromfpxfNx | fromfpxfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fromfpxl | fromfpxl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fsqrt | fsqrt | — | — | documented | [glibc catalog](./overview.md) | —decimal; decimal |
| GLIBC-fsqrtl | fsqrtl | — | — | documented | [glibc catalog](./overview.md) | —decimal; decimal |
| GLIBC-fsub | fsub | — | — | documented | [glibc catalog](./overview.md) | —decimal; decimal |
| GLIBC-fsubl | fsubl | — | — | documented | [glibc catalog](./overview.md) | —decimal; decimal |
| GLIBC-gcvt | gcvt | `stdlib.h` | — | documented | [glibc catalog](./overview.md) | —stdlib; stdlib |
| GLIBC-getpayload | getpayload | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-getpayloadf | getpayloadf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-getpayloadfN | getpayloadfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-getpayloadfNx | getpayloadfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-getpayloadl | getpayloadl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-imaxabs | imaxabs | — | — | documented | [glibc catalog](./overview.md) | —stdlib; stdlib |
| GLIBC-imaxdiv | imaxdiv | — | — | documented | [glibc catalog](./overview.md) | —stdlib; stdlib |
| GLIBC-isinf | isinf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-isinff | isinff | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-isinfl | isinfl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-isnan | isnan | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-isnanf | isnanf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-isnanl | isnanl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-labs | labs | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-ldexp | ldexp | `math.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-ldexpf | ldexpf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-ldexpfN | ldexpfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-ldexpfNx | ldexpfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-ldexpl | ldexpl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-ldiv | ldiv | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-llabs | llabs | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-lldiv | lldiv | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-llrint | llrint | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-llrintf | llrintf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-llrintfN | llrintfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-llrintfNx | llrintfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-llrintl | llrintl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-llround | llround | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-llroundf | llroundf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-llroundfN | llroundfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-llroundfNx | llroundfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-llroundl | llroundl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-lrint | lrint | `math.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-lrintf | lrintf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-lrintfN | lrintfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-lrintfNx | lrintfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-lrintl | lrintl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-lround | lround | `math.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-lroundf | lroundf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-lroundfN | lroundfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-lroundfNx | lroundfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-lroundl | lroundl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-modf | modf | `math.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-modff | modff | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-modffN | modffN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-modffNx | modffNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-modfl | modfl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-nan | nan | `math.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-nanf | nanf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-nanfN | nanfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-nanfNx | nanfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-nanl | nanl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-nearbyint | nearbyint | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-nearbyintf | nearbyintf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-nearbyintfN | nearbyintfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-nearbyintfNx | nearbyintfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-nearbyintl | nearbyintl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-nextafter | nextafter | `math.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-nextafterf | nextafterf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-nextafterfN | nextafterfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-nextafterfNx | nextafterfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-nextafterl | nextafterl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-nextdown | nextdown | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-nextdownf | nextdownf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-nextdownfN | nextdownfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-nextdownfNx | nextdownfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-nextdownl | nextdownl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-nexttoward | nexttoward | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-nexttowardf | nexttowardf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-nexttowardl | nexttowardl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-nextup | nextup | `math.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-nextupf | nextupf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-nextupfN | nextupfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-nextupfNx | nextupfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-nextupl | nextupl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-qecvt | qecvt | `stdlib.h` | — | documented | [glibc catalog](./overview.md) | —stdlib; stdlib |
| GLIBC-qecvt_r | qecvt_r | — | — | documented | [glibc catalog](./overview.md) | —stdlib; stdlib |
| GLIBC-qfcvt | qfcvt | — | — | documented | [glibc catalog](./overview.md) | —stdlib; stdlib |
| GLIBC-qfcvt_r | qfcvt_r | — | — | documented | [glibc catalog](./overview.md) | —stdlib; stdlib |
| GLIBC-qgcvt | qgcvt | — | — | documented | [glibc catalog](./overview.md) | —stdlib; stdlib |
| GLIBC-remainder | remainder | `math.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-remainderf | remainderf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-remainderfN | remainderfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-remainderfNx | remainderfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-remainderl | remainderl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-rint | rint | `math.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-rintf | rintf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-rintfN | rintfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-rintfNx | rintfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-rintl | rintl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-round | round | `math.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-roundeven | roundeven | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-roundevenf | roundevenf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-roundevenfN | roundevenfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-roundevenfNx | roundevenfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-roundevenl | roundevenl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-roundf | roundf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-roundfN | roundfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-roundfNx | roundfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-roundl | roundl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-scalb | scalb | `math.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-scalbf | scalbf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-scalbl | scalbl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-scalbln | scalbln | `math.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-scalblnf | scalblnf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-scalblnfN | scalblnfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-scalblnfNx | scalblnfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-scalblnl | scalblnl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-scalbn | scalbn | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-scalbnf | scalbnf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-scalbnfN | scalbnfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-scalbnfNx | scalbnfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-scalbnl | scalbnl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-setpayload | setpayload | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-setpayloadf | setpayloadf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-setpayloadfN | setpayloadfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-setpayloadfNx | setpayloadfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-setpayloadl | setpayloadl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-setpayloadsig | setpayloadsig | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-setpayloadsigf | setpayloadsigf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-setpayloadsigfN | setpayloadsigfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-setpayloadsigfNx | setpayloadsigfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-setpayloadsigl | setpayloadsigl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-signbit | signbit | `math.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-significand | significand | `math.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-significandf | significandf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-significandl | significandl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-strfromd | strfromd | `stdlib.h` | — | documented | [glibc catalog](./overview.md) | —stdlib; stdlib |
| GLIBC-strfromf | strfromf | — | — | documented | [glibc catalog](./overview.md) | —stdlib; stdlib |
| GLIBC-strfromfN | strfromfN | — | — | documented | [glibc catalog](./overview.md) | —stdlib; stdlib |
| GLIBC-strfromfNx | strfromfNx | — | — | documented | [glibc catalog](./overview.md) | —stdlib; stdlib |
| GLIBC-strfroml | strfroml | — | — | documented | [glibc catalog](./overview.md) | —stdlib; stdlib |
| GLIBC-strtod | strtod | `stdlib.h` | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-strtof | strtof | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-strtofN | strtofN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-strtofNx | strtofNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-strtoimax | strtoimax | `inttypes.h` | — | documented | [glibc catalog](./overview.md) | —stdlib; stdlib |
| GLIBC-strtol | strtol | `stdlib.h` | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-strtold | strtold | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-strtoll | strtoll | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-strtoq | strtoq | — | — | documented | [glibc catalog](./overview.md) | —stdlib; stdlib |
| GLIBC-strtoul | strtoul | `stdlib.h` | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-strtoull | strtoull | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-strtoumax | strtoumax | — | — | documented | [glibc catalog](./overview.md) | —stdlib; stdlib |
| GLIBC-strtouq | strtouq | — | — | documented | [glibc catalog](./overview.md) | —stdlib; stdlib |
| GLIBC-totalorder | totalorder | — | GLIBC_2.25 | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-totalorderf | totalorderf | — | GLIBC_2.25 | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-totalorderfN | totalorderfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-totalorderfNx | totalorderfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-totalorderl | totalorderl | — | GLIBC_2.25 | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-totalordermag | totalordermag | — | GLIBC_2.25 | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-totalordermagf | totalordermagf | — | GLIBC_2.25 | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-totalordermagfN | totalordermagfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-totalordermagfNx | totalordermagfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-totalordermagl | totalordermagl | — | GLIBC_2.25 | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-trunc | trunc | `math.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-truncf | truncf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-truncfN | truncfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-truncfNx | truncfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-truncl | truncl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-uabs | uabs | — | — | source-limited | [glibc catalog](./overview.md) | —stdlib; stdlib |
| GLIBC-ufromfp | ufromfp | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-ufromfpf | ufromfpf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-ufromfpfN | ufromfpfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-ufromfpfNx | ufromfpfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-ufromfpl | ufromfpl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-ufromfpx | ufromfpx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-ufromfpxf | ufromfpxf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-ufromfpxfN | ufromfpxfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-ufromfpxfNx | ufromfpxfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-ufromfpxl | ufromfpxl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-ulabs | ulabs | — | — | source-limited | [glibc catalog](./overview.md) | —stdlib; stdlib |
| GLIBC-ullabs | ullabs | — | — | source-limited | [glibc catalog](./overview.md) | —stdlib; stdlib |
| GLIBC-umaxabs | umaxabs | — | — | source-limited | [glibc catalog](./overview.md) | —stdlib; stdlib |
| GLIBC-wcstod | wcstod | — | — | documented | [glibc catalog](./overview.md) | —wide; wide |
| GLIBC-wcstof | wcstof | — | — | documented | [glibc catalog](./overview.md) | —wide; wide |
| GLIBC-wcstofN | wcstofN | — | — | documented | [glibc catalog](./overview.md) | —wide; wide |
| GLIBC-wcstofNx | wcstofNx | — | — | documented | [glibc catalog](./overview.md) | —wide; wide |
| GLIBC-wcstoimax | wcstoimax | `stddef.h` | — | documented | [glibc catalog](./overview.md) | —wide; wide |
| GLIBC-wcstol | wcstol | — | — | documented | [glibc catalog](./overview.md) | —wide; wide |
| GLIBC-wcstold | wcstold | — | — | documented | [glibc catalog](./overview.md) | —wide; wide |
| GLIBC-wcstoll | wcstoll | — | — | documented | [glibc catalog](./overview.md) | —wide; wide |
| GLIBC-wcstoq | wcstoq | — | — | documented | [glibc catalog](./overview.md) | —wide; wide |
| GLIBC-wcstoul | wcstoul | — | — | documented | [glibc catalog](./overview.md) | —wide; wide |
| GLIBC-wcstoull | wcstoull | — | — | documented | [glibc catalog](./overview.md) | —wide; wide |
| GLIBC-wcstoumax | wcstoumax | — | — | documented | [glibc catalog](./overview.md) | —wide; wide |
| GLIBC-wcstouq | wcstouq | — | — | documented | [glibc catalog](./overview.md) | —wide; wide |

### Bit Manipulation

| ID | Function | Header | Exported | Status | Chapter | Notes |
|---|---|---|---|---|---|---|
| GLIBC-stdc_bit_ceil_uc | stdc_bit_ceil_uc | — | — | documented | [glibc catalog](./overview.md) | —stdbit.h; stdbit.h |
| GLIBC-stdc_bit_ceil_ui | stdc_bit_ceil_ui | — | — | documented | [glibc catalog](./overview.md) | —stdbit.h; stdbit.h |
| GLIBC-stdc_bit_ceil_ul | stdc_bit_ceil_ul | — | — | documented | [glibc catalog](./overview.md) | —stdbit.h; stdbit.h |
| GLIBC-stdc_bit_ceil_ull | stdc_bit_ceil_ull | — | — | documented | [glibc catalog](./overview.md) | —stdbit.h; stdbit.h |
| GLIBC-stdc_bit_ceil_us | stdc_bit_ceil_us | — | — | documented | [glibc catalog](./overview.md) | —stdbit.h; stdbit.h |
| GLIBC-stdc_bit_floor_uc | stdc_bit_floor_uc | — | — | documented | [glibc catalog](./overview.md) | —stdbit.h; stdbit.h |
| GLIBC-stdc_bit_floor_ui | stdc_bit_floor_ui | — | — | documented | [glibc catalog](./overview.md) | —stdbit.h; stdbit.h |
| GLIBC-stdc_bit_floor_ul | stdc_bit_floor_ul | — | — | documented | [glibc catalog](./overview.md) | —stdbit.h; stdbit.h |
| GLIBC-stdc_bit_floor_ull | stdc_bit_floor_ull | — | — | documented | [glibc catalog](./overview.md) | —stdbit.h; stdbit.h |
| GLIBC-stdc_bit_floor_us | stdc_bit_floor_us | — | — | documented | [glibc catalog](./overview.md) | —stdbit.h; stdbit.h |
| GLIBC-stdc_bit_width_uc | stdc_bit_width_uc | — | — | documented | [glibc catalog](./overview.md) | —stdbit.h; stdbit.h |
| GLIBC-stdc_bit_width_ui | stdc_bit_width_ui | — | — | documented | [glibc catalog](./overview.md) | —stdbit.h; stdbit.h |
| GLIBC-stdc_bit_width_ul | stdc_bit_width_ul | — | — | documented | [glibc catalog](./overview.md) | —stdbit.h; stdbit.h |
| GLIBC-stdc_bit_width_ull | stdc_bit_width_ull | — | — | documented | [glibc catalog](./overview.md) | —stdbit.h; stdbit.h |
| GLIBC-stdc_bit_width_us | stdc_bit_width_us | — | — | documented | [glibc catalog](./overview.md) | —stdbit.h; stdbit.h |
| GLIBC-stdc_count_ones_uc | stdc_count_ones_uc | — | — | documented | [glibc catalog](./overview.md) | —stdbit.h; stdbit.h |
| GLIBC-stdc_count_ones_ui | stdc_count_ones_ui | — | — | documented | [glibc catalog](./overview.md) | —stdbit.h; stdbit.h |
| GLIBC-stdc_count_ones_ul | stdc_count_ones_ul | — | — | documented | [glibc catalog](./overview.md) | —stdbit.h; stdbit.h |
| GLIBC-stdc_count_ones_ull | stdc_count_ones_ull | — | — | documented | [glibc catalog](./overview.md) | —stdbit.h; stdbit.h |
| GLIBC-stdc_count_ones_us | stdc_count_ones_us | — | — | documented | [glibc catalog](./overview.md) | —stdbit.h; stdbit.h |
| GLIBC-stdc_count_zeros_uc | stdc_count_zeros_uc | — | — | documented | [glibc catalog](./overview.md) | —stdbit.h; stdbit.h |
| GLIBC-stdc_count_zeros_ui | stdc_count_zeros_ui | — | — | documented | [glibc catalog](./overview.md) | —stdbit.h; stdbit.h |
| GLIBC-stdc_count_zeros_ul | stdc_count_zeros_ul | — | — | documented | [glibc catalog](./overview.md) | —stdbit.h; stdbit.h |
| GLIBC-stdc_count_zeros_ull | stdc_count_zeros_ull | — | — | documented | [glibc catalog](./overview.md) | —stdbit.h; stdbit.h |
| GLIBC-stdc_count_zeros_us | stdc_count_zeros_us | — | — | documented | [glibc catalog](./overview.md) | —stdbit.h; stdbit.h |
| GLIBC-stdc_first_leading_one_uc | stdc_first_leading_one_uc | — | — | documented | [glibc catalog](./overview.md) | —stdbit.h; stdbit.h |
| GLIBC-stdc_first_leading_one_ui | stdc_first_leading_one_ui | — | — | documented | [glibc catalog](./overview.md) | —stdbit.h; stdbit.h |
| GLIBC-stdc_first_leading_one_ul | stdc_first_leading_one_ul | — | — | documented | [glibc catalog](./overview.md) | —stdbit.h; stdbit.h |
| GLIBC-stdc_first_leading_one_ull | stdc_first_leading_one_ull | — | — | documented | [glibc catalog](./overview.md) | —stdbit.h; stdbit.h |
| GLIBC-stdc_first_leading_one_us | stdc_first_leading_one_us | — | — | documented | [glibc catalog](./overview.md) | —stdbit.h; stdbit.h |
| GLIBC-stdc_first_leading_zero_uc | stdc_first_leading_zero_uc | — | — | documented | [glibc catalog](./overview.md) | —stdbit.h; stdbit.h |
| GLIBC-stdc_first_leading_zero_ui | stdc_first_leading_zero_ui | — | — | documented | [glibc catalog](./overview.md) | —stdbit.h; stdbit.h |
| GLIBC-stdc_first_leading_zero_ul | stdc_first_leading_zero_ul | — | — | documented | [glibc catalog](./overview.md) | —stdbit.h; stdbit.h |
| GLIBC-stdc_first_leading_zero_ull | stdc_first_leading_zero_ull | — | — | documented | [glibc catalog](./overview.md) | —stdbit.h; stdbit.h |
| GLIBC-stdc_first_leading_zero_us | stdc_first_leading_zero_us | — | — | documented | [glibc catalog](./overview.md) | —stdbit.h; stdbit.h |
| GLIBC-stdc_first_trailing_one_uc | stdc_first_trailing_one_uc | — | — | documented | [glibc catalog](./overview.md) | —stdbit.h; stdbit.h |
| GLIBC-stdc_first_trailing_one_ui | stdc_first_trailing_one_ui | — | — | documented | [glibc catalog](./overview.md) | —stdbit.h; stdbit.h |
| GLIBC-stdc_first_trailing_one_ul | stdc_first_trailing_one_ul | — | — | documented | [glibc catalog](./overview.md) | —stdbit.h; stdbit.h |
| GLIBC-stdc_first_trailing_one_ull | stdc_first_trailing_one_ull | — | — | documented | [glibc catalog](./overview.md) | —stdbit.h; stdbit.h |
| GLIBC-stdc_first_trailing_one_us | stdc_first_trailing_one_us | — | — | documented | [glibc catalog](./overview.md) | —stdbit.h; stdbit.h |
| GLIBC-stdc_first_trailing_zero_uc | stdc_first_trailing_zero_uc | — | — | documented | [glibc catalog](./overview.md) | —stdbit.h; stdbit.h |
| GLIBC-stdc_first_trailing_zero_ui | stdc_first_trailing_zero_ui | — | — | documented | [glibc catalog](./overview.md) | —stdbit.h; stdbit.h |
| GLIBC-stdc_first_trailing_zero_ul | stdc_first_trailing_zero_ul | — | — | documented | [glibc catalog](./overview.md) | —stdbit.h; stdbit.h |
| GLIBC-stdc_first_trailing_zero_ull | stdc_first_trailing_zero_ull | — | — | documented | [glibc catalog](./overview.md) | —stdbit.h; stdbit.h |
| GLIBC-stdc_first_trailing_zero_us | stdc_first_trailing_zero_us | — | — | documented | [glibc catalog](./overview.md) | —stdbit.h; stdbit.h |
| GLIBC-stdc_has_single_bit_uc | stdc_has_single_bit_uc | — | — | documented | [glibc catalog](./overview.md) | —stdbit.h; stdbit.h |
| GLIBC-stdc_has_single_bit_ui | stdc_has_single_bit_ui | — | — | documented | [glibc catalog](./overview.md) | —stdbit.h; stdbit.h |
| GLIBC-stdc_has_single_bit_ul | stdc_has_single_bit_ul | — | — | documented | [glibc catalog](./overview.md) | —stdbit.h; stdbit.h |
| GLIBC-stdc_has_single_bit_ull | stdc_has_single_bit_ull | — | — | documented | [glibc catalog](./overview.md) | —stdbit.h; stdbit.h |
| GLIBC-stdc_has_single_bit_us | stdc_has_single_bit_us | — | — | documented | [glibc catalog](./overview.md) | —stdbit.h; stdbit.h |
| GLIBC-stdc_leading_ones_uc | stdc_leading_ones_uc | — | — | documented | [glibc catalog](./overview.md) | —stdbit.h; stdbit.h |
| GLIBC-stdc_leading_ones_ui | stdc_leading_ones_ui | — | — | documented | [glibc catalog](./overview.md) | —stdbit.h; stdbit.h |
| GLIBC-stdc_leading_ones_ul | stdc_leading_ones_ul | — | — | documented | [glibc catalog](./overview.md) | —stdbit.h; stdbit.h |
| GLIBC-stdc_leading_ones_ull | stdc_leading_ones_ull | — | — | documented | [glibc catalog](./overview.md) | —stdbit.h; stdbit.h |
| GLIBC-stdc_leading_ones_us | stdc_leading_ones_us | — | — | documented | [glibc catalog](./overview.md) | —stdbit.h; stdbit.h |
| GLIBC-stdc_leading_zeros_uc | stdc_leading_zeros_uc | — | — | documented | [glibc catalog](./overview.md) | —stdbit.h; stdbit.h |
| GLIBC-stdc_leading_zeros_ui | stdc_leading_zeros_ui | — | — | documented | [glibc catalog](./overview.md) | —stdbit.h; stdbit.h |
| GLIBC-stdc_leading_zeros_ul | stdc_leading_zeros_ul | — | — | documented | [glibc catalog](./overview.md) | —stdbit.h; stdbit.h |
| GLIBC-stdc_leading_zeros_ull | stdc_leading_zeros_ull | — | — | documented | [glibc catalog](./overview.md) | —stdbit.h; stdbit.h |
| GLIBC-stdc_leading_zeros_us | stdc_leading_zeros_us | — | — | documented | [glibc catalog](./overview.md) | —stdbit.h; stdbit.h |
| GLIBC-stdc_trailing_ones_uc | stdc_trailing_ones_uc | — | — | documented | [glibc catalog](./overview.md) | —stdbit.h; stdbit.h |
| GLIBC-stdc_trailing_ones_ui | stdc_trailing_ones_ui | — | — | documented | [glibc catalog](./overview.md) | —stdbit.h; stdbit.h |
| GLIBC-stdc_trailing_ones_ul | stdc_trailing_ones_ul | — | — | documented | [glibc catalog](./overview.md) | —stdbit.h; stdbit.h |
| GLIBC-stdc_trailing_ones_ull | stdc_trailing_ones_ull | — | — | documented | [glibc catalog](./overview.md) | —stdbit.h; stdbit.h |
| GLIBC-stdc_trailing_ones_us | stdc_trailing_ones_us | — | — | documented | [glibc catalog](./overview.md) | —stdbit.h; stdbit.h |
| GLIBC-stdc_trailing_zeros_uc | stdc_trailing_zeros_uc | — | — | documented | [glibc catalog](./overview.md) | —stdbit.h; stdbit.h |
| GLIBC-stdc_trailing_zeros_ui | stdc_trailing_zeros_ui | — | — | documented | [glibc catalog](./overview.md) | —stdbit.h; stdbit.h |
| GLIBC-stdc_trailing_zeros_ul | stdc_trailing_zeros_ul | — | — | documented | [glibc catalog](./overview.md) | —stdbit.h; stdbit.h |
| GLIBC-stdc_trailing_zeros_ull | stdc_trailing_zeros_ull | — | — | documented | [glibc catalog](./overview.md) | —stdbit.h; stdbit.h |
| GLIBC-stdc_trailing_zeros_us | stdc_trailing_zeros_us | — | — | documented | [glibc catalog](./overview.md) | —stdbit.h; stdbit.h |

### Character Handling

| ID | Function | Header | Exported | Status | Chapter | Notes |
|---|---|---|---|---|---|---|
| GLIBC-_tolower | _tolower | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-_toupper | _toupper | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-isalnum | isalnum | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-isalpha | isalpha | `ctype.h` | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-isascii | isascii | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-isblank | isblank | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-iscntrl | iscntrl | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-isdigit | isdigit | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-isgraph | isgraph | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-islower | islower | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-isprint | isprint | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-ispunct | ispunct | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-isspace | isspace | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-isupper | isupper | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-iswalnum | iswalnum | `wctype.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-iswalpha | iswalpha | `wctype.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-iswblank | iswblank | `wctype.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-iswcntrl | iswcntrl | `wctype.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-iswctype | iswctype | `wctype.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-iswdigit | iswdigit | `wctype.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-iswgraph | iswgraph | `wctype.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-iswlower | iswlower | `wctype.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-iswprint | iswprint | `wctype.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-iswpunct | iswpunct | `wctype.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-iswspace | iswspace | `wctype.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-iswupper | iswupper | `wctype.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-iswxdigit | iswxdigit | `wctype.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-isxdigit | isxdigit | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-toascii | toascii | `ctype.h` | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-tolower | tolower | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-toupper | toupper | `ctype.h` | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-towctrans | towctrans | `wctype.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-towlower | towlower | `wctype.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-towupper | towupper | `wctype.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-wctrans | wctrans | `wctype.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-wctype | wctype | `wctype.h` | — | not-started | [glibc catalog](./overview.md) | — |

### Character Set Handling

| ID | Function | Header | Exported | Status | Chapter | Notes |
|---|---|---|---|---|---|---|
| GLIBC-btowc | btowc | `wchar.h` | — | documented | [glibc catalog](./overview.md) | —character; character |
| GLIBC-iconv | iconv | `iconv.h` | — | documented | [glibc catalog](./overview.md) | —character; character |
| GLIBC-iconv_close | iconv_close | `iconv.h` | — | documented | [glibc catalog](./overview.md) | —character; character |
| GLIBC-iconv_open | iconv_open | `iconv.h` | — | documented | [glibc catalog](./overview.md) | —character; character |
| GLIBC-mblen | mblen | `stdlib.h` | — | documented | [glibc catalog](./overview.md) | —character; character |
| GLIBC-mbrlen | mbrlen | `wchar.h` | — | documented | [glibc catalog](./overview.md) | —character; character |
| GLIBC-mbrtowc | mbrtowc | `wchar.h` | — | documented | [glibc catalog](./overview.md) | —character; character |
| GLIBC-mbsinit | mbsinit | `wchar.h` | — | documented | [glibc catalog](./overview.md) | —character; character |
| GLIBC-mbsnrtowcs | mbsnrtowcs | `wchar.h` | — | documented | [glibc catalog](./overview.md) | —character; character |
| GLIBC-mbsrtowcs | mbsrtowcs | `wchar.h` | — | documented | [glibc catalog](./overview.md) | —character; character |
| GLIBC-mbstowcs | mbstowcs | `stdlib.h` | — | documented | [glibc catalog](./overview.md) | —character; character |
| GLIBC-mbtowc | mbtowc | `stdlib.h` | — | documented | [glibc catalog](./overview.md) | —character; character |
| GLIBC-wcrtomb | wcrtomb | `wchar.h` | — | documented | [glibc catalog](./overview.md) | —character; character |
| GLIBC-wcsnrtombs | wcsnrtombs | `wchar.h` | — | documented | [glibc catalog](./overview.md) | —character; character |
| GLIBC-wcsrtombs | wcsrtombs | `wchar.h` | — | documented | [glibc catalog](./overview.md) | —character; character |
| GLIBC-wcstombs | wcstombs | `stdlib.h` | — | documented | [glibc catalog](./overview.md) | —character; character |
| GLIBC-wctob | wctob | `wchar.h` | — | documented | [glibc catalog](./overview.md) | —character; character |
| GLIBC-wctomb | wctomb | `stdlib.h` | — | documented | [glibc catalog](./overview.md) | —character; character |

### Cryptographic Functions

| ID | Function | Header | Exported | Status | Chapter | Notes |
|---|---|---|---|---|---|---|
| GLIBC-getentropy | getentropy | `unistd.h` | — | documented | [glibc catalog](./overview.md) | —cryptographic; cryptographic |
| GLIBC-getrandom | getrandom | — | — | documented | [glibc catalog](./overview.md) | —cryptographic; cryptographic |

### Date and Time

| ID | Function | Header | Exported | Status | Chapter | Notes |
|---|---|---|---|---|---|---|
| GLIBC-adjtime | adjtime | `sys/time.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-adjtimex | adjtimex | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-alarm | alarm | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-clock | clock | `time.h` | — | documented | [glibc catalog](./overview.md) | —FULL; FULL |
| GLIBC-clock_getres | clock_getres | — | GLIBC_2.2.5 | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-clock_gettime | clock_gettime | — | GLIBC_2.2.5 | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-clock_nanosleep | clock_nanosleep | — | GLIBC_2.2.5 | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-clock_settime | clock_settime | — | GLIBC_2.2.5 | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-difftime | difftime | `time.h` | — | documented | [glibc catalog](./overview.md) | —FULL; FULL |
| GLIBC-getdate | getdate | `time.h` | — | documented | [glibc catalog](./overview.md) | —time; time |
| GLIBC-getdate_r | getdate_r | — | — | documented | [glibc catalog](./overview.md) | —time; time |
| GLIBC-getitimer | getitimer | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-gettimeofday | gettimeofday | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-gmtime | gmtime | — | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-gmtime_r | gmtime_r | — | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-localtime | localtime | — | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-localtime_r | localtime_r | — | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-mktime | mktime | — | — | documented | [glibc catalog](./overview.md) | —FULL; FULL |
| GLIBC-nanosleep | nanosleep | — | — | documented | [glibc catalog](./overview.md) | —ledger; ledger |
| GLIBC-ntp_adjtime | ntp_adjtime | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-ntp_gettime | ntp_gettime | `sys/timex.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-setitimer | setitimer | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-settimeofday | settimeofday | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-sleep | sleep | `unistd.h` | — | documented | [glibc catalog](./overview.md) | —ledger; ledger |
| GLIBC-stime | stime | — | GLIBC_2.2.5 | documented | [glibc catalog](./overview.md) | —time; time |
| GLIBC-strftime | strftime | `time.h` | — | documented | [glibc catalog](./overview.md) | —FULL; FULL |
| GLIBC-strftime_l | strftime_l | — | — | documented | [glibc catalog](./overview.md) | —strftime; strftime |
| GLIBC-strptime | strptime | `time.h` | — | documented | [glibc catalog](./overview.md) | —FULL; FULL |
| GLIBC-time | time | — | — | documented | [glibc catalog](./overview.md) | —FULL; FULL |
| GLIBC-timegm | timegm | `time.h` | — | documented | [glibc catalog](./overview.md) | —time; time |
| GLIBC-timelocal | timelocal | — | — | documented | [glibc catalog](./overview.md) | —time; time |
| GLIBC-times | times | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-timespec_get | timespec_get | — | — | documented | [glibc catalog](./overview.md) | —time; time |
| GLIBC-timespec_getres | timespec_getres | — | — | documented | [glibc catalog](./overview.md) | —time; time |
| GLIBC-tzset | tzset | `time.h` | — | documented | [glibc catalog](./overview.md) | —FULL; FULL |
| GLIBC-wcsftime | wcsftime | — | — | documented | [glibc catalog](./overview.md) | —time; time |

### Debugging support

| ID | Function | Header | Exported | Status | Chapter | Notes |
|---|---|---|---|---|---|---|
| GLIBC-backtrace | backtrace | `execinfo.h` | — | documented | [glibc catalog](./overview.md) | —debugging; backtrace; debugging; backtrace |
| GLIBC-backtrace_symbols | backtrace_symbols | — | — | documented | [glibc catalog](./overview.md) | —debugging; backtrace; debugging; backtrace |
| GLIBC-backtrace_symbols_fd | backtrace_symbols_fd | — | — | documented | [glibc catalog](./overview.md) | —debugging; backtrace; debugging; backtrace |

### Dynamic Linker

| ID | Function | Header | Exported | Status | Chapter | Notes |
|---|---|---|---|---|---|---|
| GLIBC-_dl_find_object | _dl_find_object | — | — | documented | [glibc catalog](./overview.md) | —dynlink; dynlink |
| GLIBC-dlinfo | dlinfo | `link.h` | GLIBC_2.3.3 | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |

### Error Reporting

| ID | Function | Header | Exported | Status | Chapter | Notes |
|---|---|---|---|---|---|---|
| GLIBC-err | err | `err.h` | — | documented | [glibc catalog](./overview.md) | —err/errx/warn/warnx; err/errx/warn/warnx |
| GLIBC-error | error | `error.h` | — | documented | [glibc catalog](./overview.md) | —error/error_at_line; error/error_at_line |
| GLIBC-error_at_line | error_at_line | — | — | documented | [glibc catalog](./overview.md) | —error/error_at_line; error/error_at_line |
| GLIBC-errx | errx | — | — | documented | [glibc catalog](./overview.md) | —err/errx/warn/warnx; err/errx/warn/warnx |
| GLIBC-perror | perror | `stdio.h` | — | documented | [glibc catalog](./overview.md) | —perror; perror |
| GLIBC-strerror | strerror | `string.h` | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-strerror_l | strerror_l | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-strerror_r | strerror_r | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-strerrordesc_np | strerrordesc_np | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-strerrorname_np | strerrorname_np | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-verr | verr | — | — | documented | [glibc catalog](./overview.md) | —err/errx/warn/warnx; err/errx/warn/warnx |
| GLIBC-verrx | verrx | — | — | documented | [glibc catalog](./overview.md) | —err/errx/warn/warnx; err/errx/warn/warnx |
| GLIBC-vwarn | vwarn | — | — | documented | [glibc catalog](./overview.md) | —err/errx/warn/warnx; err/errx/warn/warnx |
| GLIBC-vwarnx | vwarnx | — | — | documented | [glibc catalog](./overview.md) | —err/errx/warn/warnx; err/errx/warn/warnx |
| GLIBC-warn | warn | — | — | documented | [glibc catalog](./overview.md) | —err/errx/warn/warnx; err/errx/warn/warnx |
| GLIBC-warnx | warnx | — | — | documented | [glibc catalog](./overview.md) | —err/errx/warn/warnx; err/errx/warn/warnx |

### File System Interface

| ID | Function | Header | Exported | Status | Chapter | Notes |
|---|---|---|---|---|---|---|
| GLIBC-access | access | — | — | documented | [glibc catalog](./overview.md) | —access/faccessat; access/faccessat |
| GLIBC-alphasort | alphasort | — | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-alphasort64 | alphasort64 | — | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-canonicalize_file_name | canonicalize_file_name | `stdlib.h` | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-chdir | chdir | — | — | documented | [glibc catalog](./overview.md) | —fs; fs |
| GLIBC-chmod | chmod | — | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-chown | chown | — | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-closedir | closedir | `sys/types.h` | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-dirfd | dirfd | `sys/types.h` | — | documented | [glibc catalog](./overview.md) | —fs; fs |
| GLIBC-DTTOIF | DTTOIF | — | — | documented | [glibc catalog](./overview.md) | —fs; fs |
| GLIBC-faccessat | faccessat | — | — | documented | [glibc catalog](./overview.md) | —access/faccessat; access/faccessat |
| GLIBC-fchdir | fchdir | — | — | documented | [glibc catalog](./overview.md) | —fs; fs |
| GLIBC-fchmod | fchmod | — | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-fchown | fchown | — | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-fdopendir | fdopendir | — | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-fstat | fstat | — | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-fstat64 | fstat64 | — | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-fstatat | fstatat | — | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-fstatat64 | fstatat64 | — | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-ftruncate | ftruncate | — | — | documented | [glibc catalog](./overview.md) | —fs; fs |
| GLIBC-ftruncate64 | ftruncate64 | — | — | documented | [glibc catalog](./overview.md) | —fs; fs |
| GLIBC-ftw | ftw | `ftw.h` | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-ftw64 | ftw64 | — | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-futimens | futimens | — | — | documented | [glibc catalog](./overview.md) | —fs; fs |
| GLIBC-futimes | futimes | `sys/time.h` | — | documented | [glibc catalog](./overview.md) | —fs; fs |
| GLIBC-get_current_dir_name | get_current_dir_name | — | — | documented | [glibc catalog](./overview.md) | —fs; fs |
| GLIBC-getcwd | getcwd | `unistd.h` | — | documented | [glibc catalog](./overview.md) | —fs; fs |
| GLIBC-getdents64 | getdents64 | — | — | documented | [glibc catalog](./overview.md) | —fs; fs |
| GLIBC-getumask | getumask | — | — | source-limited | [glibc catalog](./overview.md) | —fs; fs |
| GLIBC-IFTODT | IFTODT | — | — | documented | [glibc catalog](./overview.md) | —fs; fs |
| GLIBC-link | link | — | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-linkat | linkat | — | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-lstat | lstat | — | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-lstat64 | lstat64 | — | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-lutimes | lutimes | — | — | documented | [glibc catalog](./overview.md) | —fs; fs |
| GLIBC-mkdir | mkdir | — | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-mkdirat | mkdirat | — | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-mkdtemp | mkdtemp | `stdlib.h` | — | documented | [glibc catalog](./overview.md) | —tmpfile/tmpnam/mkstemp/mkdtemp; Grouped; tmpfile/tmpnam/mkstemp/mkdtemp; Grouped |
| GLIBC-mknod | mknod | — | — | documented | [glibc catalog](./overview.md) | —fs; fs |
| GLIBC-mkstemp | mkstemp | `stdlib.h` | — | documented | [glibc catalog](./overview.md) | —tmpfile/tmpnam/mkstemp/mkdtemp; Grouped; tmpfile/tmpnam/mkstemp/mkdtemp; Grouped |
| GLIBC-mktemp | mktemp | `stdlib.h` | — | documented | [glibc catalog](./overview.md) | —tmpfile/tmpnam/mkstemp/mkdtemp; tmpfile/tmpnam/mkstemp/mkdtemp |
| GLIBC-nftw | nftw | — | GLIBC_2.2.5 | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-nftw64 | nftw64 | — | GLIBC_2.2.5 | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-opendir | opendir | `sys/types.h` | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-posix_fallocate | posix_fallocate | `fcntl.h` | — | documented | [glibc catalog](./overview.md) | —fs; fs |
| GLIBC-posix_fallocate64 | posix_fallocate64 | — | — | documented | [glibc catalog](./overview.md) | —fs; fs |
| GLIBC-readdir | readdir | `dirent.h` | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-readdir64 | readdir64 | — | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-readdir64_r | readdir64_r | — | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-readdir_r | readdir_r | `dirent.h` | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-readlink | readlink | — | — | documented | [glibc catalog](./overview.md) | —fs; fs |
| GLIBC-realpath | realpath | `limits.h` | GLIBC_2.2.5 | documented | [glibc catalog](./overview.md) | —FULL; FULL |
| GLIBC-remove | remove | `stdio.h` | — | documented | [glibc catalog](./overview.md) | —remove/rename; Grouped; remove/rename; Grouped |
| GLIBC-rename | rename | — | — | documented | [glibc catalog](./overview.md) | —remove/rename; Grouped; remove/rename; Grouped |
| GLIBC-renameat | renameat | — | — | documented | [glibc catalog](./overview.md) | —remove/rename; Grouped; remove/rename; Grouped |
| GLIBC-rewinddir | rewinddir | `sys/types.h` | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-rmdir | rmdir | — | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-scandir | scandir | `dirent.h` | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-scandir64 | scandir64 | — | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-seekdir | seekdir | `dirent.h` | — | documented | [glibc catalog](./overview.md) | —fs; fs |
| GLIBC-stat | stat | — | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-stat64 | stat64 | — | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-symlink | symlink | — | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-telldir | telldir | `dirent.h` | — | documented | [glibc catalog](./overview.md) | —fs; fs |
| GLIBC-tempnam | tempnam | `stdio.h` | — | documented | [glibc catalog](./overview.md) | —tmpfile/tmpnam/mkstemp/mkdtemp; tmpfile/tmpnam/mkstemp/mkdtemp |
| GLIBC-tmpfile | tmpfile | `stdio.h` | — | documented | [glibc catalog](./overview.md) | —tmpfile/tmpnam/mkstemp/mkdtemp; tmpfile/tmpnam/mkstemp/mkdtemp |
| GLIBC-tmpfile64 | tmpfile64 | — | — | documented | [glibc catalog](./overview.md) | —tmpfile/tmpnam/mkstemp/mkdtemp; tmpfile/tmpnam/mkstemp/mkdtemp |
| GLIBC-tmpnam | tmpnam | `stdio.h` | — | documented | [glibc catalog](./overview.md) | —tmpfile/tmpnam/mkstemp/mkdtemp; tmpfile/tmpnam/mkstemp/mkdtemp |
| GLIBC-tmpnam_r | tmpnam_r | — | — | documented | [glibc catalog](./overview.md) | —tmpfile/tmpnam/mkstemp/mkdtemp; tmpfile/tmpnam/mkstemp/mkdtemp |
| GLIBC-truncate | truncate | — | — | documented | [glibc catalog](./overview.md) | —fs; fs |
| GLIBC-truncate64 | truncate64 | — | — | documented | [glibc catalog](./overview.md) | —fs; fs |
| GLIBC-umask | umask | — | — | documented | [glibc catalog](./overview.md) | —fs; fs |
| GLIBC-unlink | unlink | — | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-unlinkat | unlinkat | — | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-utime | utime | — | — | documented | [glibc catalog](./overview.md) | —fs; fs |
| GLIBC-utimensat | utimensat | — | — | documented | [glibc catalog](./overview.md) | —fs; fs |
| GLIBC-utimes | utimes | — | — | documented | [glibc catalog](./overview.md) | —fs; fs |
| GLIBC-versionsort | versionsort | — | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-versionsort64 | versionsort64 | — | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |

### Input/Output on Streams

| ID | Function | Header | Exported | Status | Chapter | Notes |
|---|---|---|---|---|---|---|
| GLIBC-__fbufsize | __fbufsize | — | — | documented | [glibc catalog](./overview.md) | —stdio_ext; stdio_ext |
| GLIBC-__flbf | __flbf | — | — | documented | [glibc catalog](./overview.md) | —stdio_ext; stdio_ext |
| GLIBC-__fpending | __fpending | — | — | documented | [glibc catalog](./overview.md) | —stdio_ext; stdio_ext |
| GLIBC-__fpurge | __fpurge | — | — | documented | [glibc catalog](./overview.md) | —stdio_ext; stdio_ext |
| GLIBC-__freadable | __freadable | — | — | documented | [glibc catalog](./overview.md) | —stdio_ext; stdio_ext |
| GLIBC-__freading | __freading | — | — | documented | [glibc catalog](./overview.md) | —stdio_ext; stdio_ext |
| GLIBC-__fsetlocking | __fsetlocking | — | — | documented | [glibc catalog](./overview.md) | —stdio_ext; stdio_ext |
| GLIBC-__fwritable | __fwritable | — | — | documented | [glibc catalog](./overview.md) | —stdio_ext; stdio_ext |
| GLIBC-__fwriting | __fwriting | — | — | documented | [glibc catalog](./overview.md) | —stdio_ext; stdio_ext |
| GLIBC-_flushlbf | _flushlbf | — | — | documented | [glibc catalog](./overview.md) | —stdio_ext; stdio_ext |
| GLIBC-addseverity | addseverity | `fmtmsg.h` | — | documented | [glibc catalog](./overview.md) | —fmtmsg/addseverity; fmtmsg/addseverity |
| GLIBC-asprintf | asprintf | `stdio.h` | — | documented | [glibc catalog](./overview.md) | —printf; printf |
| GLIBC-clearerr | clearerr | — | — | documented | [glibc catalog](./overview.md) | —fileno/feof/ferror/clearerr; fileno/feof/ferror/clearerr |
| GLIBC-clearerr_unlocked | clearerr_unlocked | — | — | documented | [glibc catalog](./overview.md) | —fileno/feof/ferror/clearerr; fileno/feof/ferror/clearerr |
| GLIBC-dprintf | dprintf | — | — | documented | [glibc catalog](./overview.md) | —printf; printf |
| GLIBC-fclose | fclose | `stdio.h` | — | documented | [glibc catalog](./overview.md) | —fopen/fdopen/freopen/fclose; fopen/fdopen/freopen/fclose |
| GLIBC-fcloseall | fcloseall | `stdio.h` | — | documented | [glibc catalog](./overview.md) | —fopen/fdopen/freopen/fclose; fopen/fdopen/freopen/fclose |
| GLIBC-feof | feof | — | — | documented | [glibc catalog](./overview.md) | —fileno/feof/ferror/clearerr; fileno/feof/ferror/clearerr |
| GLIBC-feof_unlocked | feof_unlocked | — | — | documented | [glibc catalog](./overview.md) | —fileno/feof/ferror/clearerr; fileno/feof/ferror/clearerr |
| GLIBC-ferror | ferror | `stdio.h` | — | documented | [glibc catalog](./overview.md) | —fileno/feof/ferror/clearerr; fileno/feof/ferror/clearerr |
| GLIBC-ferror_unlocked | ferror_unlocked | — | — | documented | [glibc catalog](./overview.md) | —fileno/feof/ferror/clearerr; fileno/feof/ferror/clearerr |
| GLIBC-fflush | fflush | `stdio.h` | — | documented | [glibc catalog](./overview.md) | —fflush; fflush |
| GLIBC-fflush_unlocked | fflush_unlocked | — | — | documented | [glibc catalog](./overview.md) | —fflush; fflush |
| GLIBC-fgetc | fgetc | `stdio.h` | — | documented | [glibc catalog](./overview.md) | —fgetc/getc/getchar/ungetc; fgetc/getc/getchar/ungetc |
| GLIBC-fgetc_unlocked | fgetc_unlocked | — | — | documented | [glibc catalog](./overview.md) | —fgetc/getc/getchar/ungetc; fgetc/getc/getchar/ungetc |
| GLIBC-fgetpos | fgetpos | — | — | documented | [glibc catalog](./overview.md) | —fseeko/ftello; fseeko/ftello |
| GLIBC-fgetpos64 | fgetpos64 | — | — | documented | [glibc catalog](./overview.md) | —fseeko/ftello; fseeko/ftello |
| GLIBC-fgets | fgets | — | — | documented | [glibc catalog](./overview.md) | —fgets/getline/getdelim; fgets/getline/getdelim |
| GLIBC-fgets_unlocked | fgets_unlocked | — | — | documented | [glibc catalog](./overview.md) | —fgets/getline/getdelim; fgets/getline/getdelim |
| GLIBC-fgetwc | fgetwc | `stdio.h` | — | documented | [glibc catalog](./overview.md) | —wide-char; wide-char |
| GLIBC-fgetwc_unlocked | fgetwc_unlocked | — | — | documented | [glibc catalog](./overview.md) | —wide-char; wide-char |
| GLIBC-fgetws | fgetws | `wchar.h` | — | documented | [glibc catalog](./overview.md) | —wide-char; wide-char |
| GLIBC-fgetws_unlocked | fgetws_unlocked | — | — | documented | [glibc catalog](./overview.md) | —wide-char; wide-char |
| GLIBC-flockfile | flockfile | `stdio.h` | — | documented | [glibc catalog](./overview.md) | —flockfile; flockfile |
| GLIBC-fmemopen | fmemopen | `stdio.h` | GLIBC_2.2.5 | documented | [glibc catalog](./overview.md) | —fmemopen/open_memstream/fopencookie; fmemopen/open_memstream/fopencookie |
| GLIBC-fmtmsg | fmtmsg | `fmtmsg.h` | — | documented | [glibc catalog](./overview.md) | —fmtmsg/addseverity; fmtmsg/addseverity |
| GLIBC-fopen | fopen | `stdio.h` | — | documented | [glibc catalog](./overview.md) | —fopen/fdopen/freopen/fclose; fopen/fdopen/freopen/fclose |
| GLIBC-fopen64 | fopen64 | — | — | documented | [glibc catalog](./overview.md) | —fopen/fdopen/freopen/fclose; fopen/fdopen/freopen/fclose |
| GLIBC-fopencookie | fopencookie | `stdio.h` | — | documented | [glibc catalog](./overview.md) | —fmemopen/open_memstream/fopencookie; fmemopen/open_memstream/fopencookie |
| GLIBC-fprintf | fprintf | — | — | documented | [glibc catalog](./overview.md) | —printf; printf |
| GLIBC-fputc | fputc | — | — | documented | [glibc catalog](./overview.md) | —fputc/putc/putchar/fputs/puts; fputc/putc/putchar/fputs/puts |
| GLIBC-fputc_unlocked | fputc_unlocked | — | — | documented | [glibc catalog](./overview.md) | —fputc/putc/putchar/fputs/puts; fputc/putc/putchar/fputs/puts |
| GLIBC-fputs | fputs | — | — | documented | [glibc catalog](./overview.md) | —fputc/putc/putchar/fputs/puts; fputc/putc/putchar/fputs/puts |
| GLIBC-fputs_unlocked | fputs_unlocked | — | — | documented | [glibc catalog](./overview.md) | —fputc/putc/putchar/fputs/puts; fputc/putc/putchar/fputs/puts |
| GLIBC-fputwc | fputwc | `stdio.h` | — | documented | [glibc catalog](./overview.md) | —wide-char; wide-char |
| GLIBC-fputwc_unlocked | fputwc_unlocked | — | — | documented | [glibc catalog](./overview.md) | —wide-char; wide-char |
| GLIBC-fputws | fputws | `wchar.h` | — | documented | [glibc catalog](./overview.md) | —wide-char; wide-char |
| GLIBC-fputws_unlocked | fputws_unlocked | — | — | documented | [glibc catalog](./overview.md) | —wide-char; wide-char |
| GLIBC-fread | fread | `stdio.h` | — | documented | [glibc catalog](./overview.md) | —fread/fwrite; fread/fwrite |
| GLIBC-fread_unlocked | fread_unlocked | — | — | documented | [glibc catalog](./overview.md) | —fread/fwrite; fread/fwrite |
| GLIBC-freopen | freopen | — | — | documented | [glibc catalog](./overview.md) | —fopen/fdopen/freopen/fclose; fopen/fdopen/freopen/fclose |
| GLIBC-freopen64 | freopen64 | — | — | documented | [glibc catalog](./overview.md) | —fopen/fdopen/freopen/fclose; fopen/fdopen/freopen/fclose |
| GLIBC-fscanf | fscanf | — | — | documented | [glibc catalog](./overview.md) | —scanf; scanf |
| GLIBC-fseek | fseek | `stdio.h` | — | documented | [glibc catalog](./overview.md) | —fseeko/ftello; fseeko/ftello |
| GLIBC-fseeko | fseeko | `stdio.h` | — | documented | [glibc catalog](./overview.md) | —fseeko/ftello; fseeko/ftello |
| GLIBC-fseeko64 | fseeko64 | — | — | documented | [glibc catalog](./overview.md) | —fseeko/ftello; fseeko/ftello |
| GLIBC-fsetpos | fsetpos | — | — | documented | [glibc catalog](./overview.md) | —fseeko/ftello; fseeko/ftello |
| GLIBC-fsetpos64 | fsetpos64 | — | — | documented | [glibc catalog](./overview.md) | —fseeko/ftello; fseeko/ftello |
| GLIBC-ftell | ftell | — | — | documented | [glibc catalog](./overview.md) | —fseeko/ftello; fseeko/ftello |
| GLIBC-ftello | ftello | — | — | documented | [glibc catalog](./overview.md) | —fseeko/ftello; fseeko/ftello |
| GLIBC-ftello64 | ftello64 | — | — | documented | [glibc catalog](./overview.md) | —fseeko/ftello; fseeko/ftello |
| GLIBC-ftrylockfile | ftrylockfile | — | — | documented | [glibc catalog](./overview.md) | —flockfile; flockfile |
| GLIBC-funlockfile | funlockfile | — | — | documented | [glibc catalog](./overview.md) | —flockfile; flockfile |
| GLIBC-fwide | fwide | `wchar.h` | — | documented | [glibc catalog](./overview.md) | —wide-char; wide-char |
| GLIBC-fwprintf | fwprintf | — | — | documented | [glibc catalog](./overview.md) | —wide-char; wide-char |
| GLIBC-fwrite | fwrite | — | — | documented | [glibc catalog](./overview.md) | —fread/fwrite; fread/fwrite |
| GLIBC-fwrite_unlocked | fwrite_unlocked | — | — | documented | [glibc catalog](./overview.md) | —fread/fwrite; fread/fwrite |
| GLIBC-fwscanf | fwscanf | — | — | documented | [glibc catalog](./overview.md) | —wide-char; wide-char |
| GLIBC-getc | getc | — | — | documented | [glibc catalog](./overview.md) | —fgetc/getc/getchar/ungetc; fgetc/getc/getchar/ungetc |
| GLIBC-getc_unlocked | getc_unlocked | — | — | documented | [glibc catalog](./overview.md) | —fgetc/getc/getchar/ungetc; fgetc/getc/getchar/ungetc |
| GLIBC-getchar | getchar | — | — | documented | [glibc catalog](./overview.md) | —fgetc/getc/getchar/ungetc; fgetc/getc/getchar/ungetc |
| GLIBC-getchar_unlocked | getchar_unlocked | — | — | documented | [glibc catalog](./overview.md) | —fgetc/getc/getchar/ungetc; fgetc/getc/getchar/ungetc |
| GLIBC-getdelim | getdelim | — | — | documented | [glibc catalog](./overview.md) | —fgets/getline/getdelim; fgets/getline/getdelim |
| GLIBC-getline | getline | `stdio.h` | — | documented | [glibc catalog](./overview.md) | —fgets/getline/getdelim; fgets/getline/getdelim |
| GLIBC-getw | getw | `stdio.h` | — | documented | [glibc catalog](./overview.md) | —fgetc/getc/getchar/ungetc; fgetc/getc/getchar/ungetc |
| GLIBC-getwc | getwc | — | — | documented | [glibc catalog](./overview.md) | —wide-char; wide-char |
| GLIBC-getwc_unlocked | getwc_unlocked | — | — | documented | [glibc catalog](./overview.md) | —wide-char; wide-char |
| GLIBC-getwchar | getwchar | `wchar.h` | — | documented | [glibc catalog](./overview.md) | —wide-char; wide-char |
| GLIBC-getwchar_unlocked | getwchar_unlocked | — | — | documented | [glibc catalog](./overview.md) | —wide-char; wide-char |
| GLIBC-obstack_printf | obstack_printf | — | — | documented | [glibc catalog](./overview.md) | —obstack; obstack |
| GLIBC-obstack_vprintf | obstack_vprintf | — | — | documented | [glibc catalog](./overview.md) | —obstack; obstack |
| GLIBC-open_memstream | open_memstream | `stdio.h` | — | documented | [glibc catalog](./overview.md) | —fmemopen/open_memstream/fopencookie; fmemopen/open_memstream/fopencookie |
| GLIBC-parse_printf_format | parse_printf_format | — | — | documented | [glibc catalog](./overview.md) | —parse_printf_format/printf_size; parse_printf_format/printf_size |
| GLIBC-printf | printf | `stdio.h` | — | documented | [glibc catalog](./overview.md) | —printf; printf |
| GLIBC-printf_size | printf_size | — | — | documented | [glibc catalog](./overview.md) | —parse_printf_format/printf_size; parse_printf_format/printf_size |
| GLIBC-printf_size_info | printf_size_info | — | — | documented | [glibc catalog](./overview.md) | —parse_printf_format/printf_size; parse_printf_format/printf_size |
| GLIBC-putc | putc | — | — | documented | [glibc catalog](./overview.md) | —fputc/putc/putchar/fputs/puts; fputc/putc/putchar/fputs/puts |
| GLIBC-putc_unlocked | putc_unlocked | — | — | documented | [glibc catalog](./overview.md) | —fputc/putc/putchar/fputs/puts; fputc/putc/putchar/fputs/puts |
| GLIBC-putchar | putchar | — | — | documented | [glibc catalog](./overview.md) | —fputc/putc/putchar/fputs/puts; fputc/putc/putchar/fputs/puts |
| GLIBC-putchar_unlocked | putchar_unlocked | — | — | documented | [glibc catalog](./overview.md) | —fputc/putc/putchar/fputs/puts; fputc/putc/putchar/fputs/puts |
| GLIBC-puts | puts | `stdio.h` | — | documented | [glibc catalog](./overview.md) | —fputc/putc/putchar/fputs/puts; fputc/putc/putchar/fputs/puts |
| GLIBC-putw | putw | — | — | documented | [glibc catalog](./overview.md) | —fputc/putc/putchar/fputs/puts; fputc/putc/putchar/fputs/puts |
| GLIBC-putwc | putwc | — | — | documented | [glibc catalog](./overview.md) | —wide-char; wide-char |
| GLIBC-putwc_unlocked | putwc_unlocked | — | — | documented | [glibc catalog](./overview.md) | —wide-char; wide-char |
| GLIBC-putwchar | putwchar | `wchar.h` | — | documented | [glibc catalog](./overview.md) | —wide-char; wide-char |
| GLIBC-putwchar_unlocked | putwchar_unlocked | — | — | documented | [glibc catalog](./overview.md) | —wide-char; wide-char |
| GLIBC-register_printf_function | register_printf_function | — | — | documented | [glibc catalog](./overview.md) | —register_printf_function; register_printf_function |
| GLIBC-rewind | rewind | — | — | documented | [glibc catalog](./overview.md) | —fseeko/ftello; fseeko/ftello |
| GLIBC-scanf | scanf | `stdio.h` | — | documented | [glibc catalog](./overview.md) | —scanf; scanf |
| GLIBC-setbuf | setbuf | `stdio.h` | — | documented | [glibc catalog](./overview.md) | —setvbuf/setbuf/setbuffer; setvbuf/setbuf/setbuffer |
| GLIBC-setbuffer | setbuffer | — | — | documented | [glibc catalog](./overview.md) | —setvbuf/setbuf/setbuffer; setvbuf/setbuf/setbuffer |
| GLIBC-setlinebuf | setlinebuf | — | — | documented | [glibc catalog](./overview.md) | —setvbuf/setbuf/setbuffer; setvbuf/setbuf/setbuffer |
| GLIBC-setvbuf | setvbuf | — | — | documented | [glibc catalog](./overview.md) | —setvbuf/setbuf/setbuffer; setvbuf/setbuf/setbuffer |
| GLIBC-snprintf | snprintf | — | — | documented | [glibc catalog](./overview.md) | —printf; printf |
| GLIBC-sprintf | sprintf | — | — | documented | [glibc catalog](./overview.md) | —printf; printf |
| GLIBC-sscanf | sscanf | — | — | documented | [glibc catalog](./overview.md) | —scanf; scanf |
| GLIBC-swprintf | swprintf | — | — | documented | [glibc catalog](./overview.md) | —wide-char; wide-char |
| GLIBC-swscanf | swscanf | — | — | documented | [glibc catalog](./overview.md) | —wide-char; wide-char |
| GLIBC-ungetc | ungetc | — | — | documented | [glibc catalog](./overview.md) | —fgetc/getc/getchar/ungetc; fgetc/getc/getchar/ungetc |
| GLIBC-ungetwc | ungetwc | `wchar.h` | — | documented | [glibc catalog](./overview.md) | —wide-char; wide-char |
| GLIBC-vasprintf | vasprintf | — | — | documented | [glibc catalog](./overview.md) | —vprintf; vprintf |
| GLIBC-vdprintf | vdprintf | — | — | documented | [glibc catalog](./overview.md) | —vprintf; vprintf |
| GLIBC-vfprintf | vfprintf | — | — | documented | [glibc catalog](./overview.md) | —vprintf; vprintf |
| GLIBC-vfscanf | vfscanf | — | — | documented | [glibc catalog](./overview.md) | —scanf; scanf |
| GLIBC-vfwprintf | vfwprintf | — | — | documented | [glibc catalog](./overview.md) | —wide-char; wide-char |
| GLIBC-vfwscanf | vfwscanf | — | — | documented | [glibc catalog](./overview.md) | —wide-char; wide-char |
| GLIBC-vprintf | vprintf | — | — | documented | [glibc catalog](./overview.md) | —vprintf; vprintf |
| GLIBC-vscanf | vscanf | — | — | documented | [glibc catalog](./overview.md) | —scanf; scanf |
| GLIBC-vsnprintf | vsnprintf | — | — | documented | [glibc catalog](./overview.md) | —vprintf; vprintf |
| GLIBC-vsprintf | vsprintf | — | — | documented | [glibc catalog](./overview.md) | —vprintf; vprintf |
| GLIBC-vsscanf | vsscanf | — | — | documented | [glibc catalog](./overview.md) | —scanf; scanf |
| GLIBC-vswprintf | vswprintf | — | — | documented | [glibc catalog](./overview.md) | —wide-char; wide-char |
| GLIBC-vswscanf | vswscanf | — | — | documented | [glibc catalog](./overview.md) | —wide-char; wide-char |
| GLIBC-vwprintf | vwprintf | — | — | documented | [glibc catalog](./overview.md) | —wide-char; wide-char |
| GLIBC-vwscanf | vwscanf | — | — | documented | [glibc catalog](./overview.md) | —wide-char; wide-char |
| GLIBC-wprintf | wprintf | `stdio.h` | — | documented | [glibc catalog](./overview.md) | —wide-char; wide-char |
| GLIBC-wscanf | wscanf | — | — | documented | [glibc catalog](./overview.md) | —wide-char; wide-char |

### Inter-Process Communication

| ID | Function | Header | Exported | Status | Chapter | Notes |
|---|---|---|---|---|---|---|
| GLIBC-semctl | semctl | — | — | documented | [glibc catalog](./overview.md) | —sysv; sysv |
| GLIBC-semget | semget | — | — | documented | [glibc catalog](./overview.md) | —sysv; sysv |
| GLIBC-semop | semop | — | — | documented | [glibc catalog](./overview.md) | —sysv; sysv |
| GLIBC-semtimedop | semtimedop | — | — | documented | [glibc catalog](./overview.md) | —sysv; sysv |

### Job Control

| ID | Function | Header | Exported | Status | Chapter | Notes |
|---|---|---|---|---|---|---|
| GLIBC-ctermid | ctermid | `stdio.h` | — | documented | [glibc catalog](./overview.md) | —job; job |
| GLIBC-getpgid | getpgid | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-getpgrp | getpgrp | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-getsid | getsid | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-setpgid | setpgid | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-setpgrp | setpgrp | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-setsid | setsid | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-tcgetpgrp | tcgetpgrp | `unistd.h` | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-tcgetsid | tcgetsid | `termios.h` | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-tcsetpgrp | tcsetpgrp | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |

### Locales and Internationalization

| ID | Function | Header | Exported | Status | Chapter | Notes |
|---|---|---|---|---|---|---|
| GLIBC-localeconv | localeconv | `locale.h` | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-nl_langinfo | nl_langinfo | `langinfo.h` | — | documented | [glibc catalog](./overview.md) | —compact; compact |
| GLIBC-rpmatch | rpmatch | `stdlib.h` | — | documented | [glibc catalog](./overview.md) | —compact; compact |
| GLIBC-setlocale | setlocale | `locale.h` | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-strfmon | strfmon | `monetary.h` | — | documented | [glibc catalog](./overview.md) | —compact; compact |

### Low-Level Input/Output

| ID | Function | Header | Exported | Status | Chapter | Notes |
|---|---|---|---|---|---|---|
| GLIBC-aio_cancel | aio_cancel | `aio.h` | GLIBC_2.2.5 | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-aio_cancel64 | aio_cancel64 | — | GLIBC_2.2.5 | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-aio_error | aio_error | `aio.h` | GLIBC_2.2.5 | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-aio_error64 | aio_error64 | — | GLIBC_2.2.5 | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-aio_fsync | aio_fsync | `aio.h` | GLIBC_2.2.5 | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-aio_fsync64 | aio_fsync64 | — | GLIBC_2.2.5 | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-aio_init | aio_init | `aio.h` | GLIBC_2.2.5 | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-aio_read | aio_read | `aio.h` | GLIBC_2.2.5 | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-aio_read64 | aio_read64 | — | GLIBC_2.2.5 | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-aio_return | aio_return | `aio.h` | GLIBC_2.2.5 | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-aio_return64 | aio_return64 | — | GLIBC_2.2.5 | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-aio_suspend | aio_suspend | `aio.h` | GLIBC_2.2.5 | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-aio_suspend64 | aio_suspend64 | — | GLIBC_2.2.5 | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-aio_write | aio_write | `aio.h` | GLIBC_2.2.5 | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-aio_write64 | aio_write64 | — | GLIBC_2.2.5 | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-close | close | — | — | documented | [glibc catalog](./overview.md) | —open/close; open/close |
| GLIBC-close_range | close_range | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-closefrom | closefrom | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-copy_file_range | copy_file_range | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-dup | dup | — | — | documented | [glibc catalog](./overview.md) | —dup/dup2/dup3; dup/dup2/dup3 |
| GLIBC-dup2 | dup2 | — | — | documented | [glibc catalog](./overview.md) | —dup/dup2/dup3; dup/dup2/dup3 |
| GLIBC-dup3 | dup3 | — | — | documented | [glibc catalog](./overview.md) | —dup/dup2/dup3; dup/dup2/dup3 |
| GLIBC-epoll_create | epoll_create | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-epoll_wait | epoll_wait | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fcntl | fcntl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-fdatasync | fdatasync | — | — | documented | [glibc catalog](./overview.md) | —fsync/fdatasync; fsync/fdatasync |
| GLIBC-fdopen | fdopen | — | — | documented | [glibc catalog](./overview.md) | —fopen; fopen |
| GLIBC-fileno | fileno | `stdio.h` | — | documented | [glibc catalog](./overview.md) | —fileno/feof/ferror/clearerr; fileno/feof/ferror/clearerr |
| GLIBC-fileno_unlocked | fileno_unlocked | — | — | documented | [glibc catalog](./overview.md) | —fileno/feof/ferror/clearerr; fileno/feof/ferror/clearerr |
| GLIBC-fsync | fsync | — | — | documented | [glibc catalog](./overview.md) | —fsync/fdatasync; fsync/fdatasync |
| GLIBC-ioctl | ioctl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-lio_listio | lio_listio | `aio.h` | GLIBC_2.4 | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-lio_listio64 | lio_listio64 | — | GLIBC_2.4 | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-lseek | lseek | — | — | documented | [glibc catalog](./overview.md) | —lseek; lseek |
| GLIBC-lseek64 | lseek64 | `sys/types.h` | — | documented | [glibc catalog](./overview.md) | —lseek; lseek |
| GLIBC-madvise | madvise | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-memfd_create | memfd_create | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-mmap | mmap | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-mmap64 | mmap64 | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-mremap | mremap | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-msync | msync | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-munmap | munmap | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-open | open | — | — | documented | [glibc catalog](./overview.md) | —open/close; open/close |
| GLIBC-open64 | open64 | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-openat | openat | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-openat2 | openat2 | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-openat64 | openat64 | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-poll | poll | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-pread | pread | — | — | documented | [glibc catalog](./overview.md) | —readv/writev/pread/pwrite; readv/writev/pread/pwrite |
| GLIBC-pread64 | pread64 | — | — | documented | [glibc catalog](./overview.md) | —readv/writev/pread/pwrite; readv/writev/pread/pwrite |
| GLIBC-preadv | preadv | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-preadv2 | preadv2 | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-preadv64 | preadv64 | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-preadv64v2 | preadv64v2 | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-pwrite | pwrite | — | — | documented | [glibc catalog](./overview.md) | —readv/writev/pread/pwrite; readv/writev/pread/pwrite |
| GLIBC-pwrite64 | pwrite64 | — | — | documented | [glibc catalog](./overview.md) | —readv/writev/pread/pwrite; readv/writev/pread/pwrite |
| GLIBC-pwritev | pwritev | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-pwritev2 | pwritev2 | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-pwritev64 | pwritev64 | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-pwritev64v2 | pwritev64v2 | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-read | read | — | — | documented | [glibc catalog](./overview.md) | —read/write; read/write |
| GLIBC-readv | readv | — | — | documented | [glibc catalog](./overview.md) | —readv/writev/pread/pwrite; readv/writev/pread/pwrite |
| GLIBC-select | select | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-sync | sync | — | — | documented | [glibc catalog](./overview.md) | —sync; sync |
| GLIBC-write | write | — | — | documented | [glibc catalog](./overview.md) | —read/write; read/write |
| GLIBC-writev | writev | — | — | documented | [glibc catalog](./overview.md) | —readv/writev/pread/pwrite; readv/writev/pread/pwrite |

### Low-Level Terminal Interface

| ID | Function | Header | Exported | Status | Chapter | Notes |
|---|---|---|---|---|---|---|
| GLIBC-cfgetibaud | cfgetibaud | — | — | documented | [glibc catalog](./overview.md) | —legacy; legacy |
| GLIBC-cfgetispeed | cfgetispeed | — | — | documented | [glibc catalog](./overview.md) | —baud; baud |
| GLIBC-cfgetobaud | cfgetobaud | — | — | documented | [glibc catalog](./overview.md) | —legacy; legacy |
| GLIBC-cfgetospeed | cfgetospeed | — | — | documented | [glibc catalog](./overview.md) | —baud; baud |
| GLIBC-cfmakeraw | cfmakeraw | — | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-cfsetbaud | cfsetbaud | — | — | documented | [glibc catalog](./overview.md) | —legacy; legacy |
| GLIBC-cfsetibaud | cfsetibaud | — | — | documented | [glibc catalog](./overview.md) | —legacy; legacy |
| GLIBC-cfsetispeed | cfsetispeed | — | — | documented | [glibc catalog](./overview.md) | —baud; baud |
| GLIBC-cfsetobaud | cfsetobaud | — | — | documented | [glibc catalog](./overview.md) | —legacy; legacy |
| GLIBC-cfsetospeed | cfsetospeed | — | — | documented | [glibc catalog](./overview.md) | —baud; baud |
| GLIBC-cfsetspeed | cfsetspeed | — | — | documented | [glibc catalog](./overview.md) | —baud; baud |
| GLIBC-forkpty | forkpty | — | GLIBC_2.2.5 | documented | [glibc catalog](./overview.md) | —pty; pty |
| GLIBC-getpass | getpass | `unistd.h` | — | documented | [glibc catalog](./overview.md) | —terminal; terminal |
| GLIBC-getpt | getpt | `stdlib.h` | — | documented | [glibc catalog](./overview.md) | —pty; pty |
| GLIBC-grantpt | grantpt | `stdlib.h` | — | documented | [glibc catalog](./overview.md) | —pty; pty |
| GLIBC-gtty | gtty | — | — | documented | [glibc catalog](./overview.md) | —sgtty; sgtty |
| GLIBC-isatty | isatty | `unistd.h` | — | documented | [glibc catalog](./overview.md) | —isatty; isatty |
| GLIBC-openpty | openpty | `pty.h` | GLIBC_2.2.5 | documented | [glibc catalog](./overview.md) | —pty; pty |
| GLIBC-posix_openpt | posix_openpt | `stdlib.h` | — | documented | [glibc catalog](./overview.md) | —pty; pty |
| GLIBC-ptsname | ptsname | `stdlib.h` | — | documented | [glibc catalog](./overview.md) | —pty; pty |
| GLIBC-ptsname_r | ptsname_r | — | — | documented | [glibc catalog](./overview.md) | —pty; pty |
| GLIBC-stty | stty | — | — | documented | [glibc catalog](./overview.md) | —sgtty; sgtty |
| GLIBC-tcdrain | tcdrain | — | — | documented | [glibc catalog](./overview.md) | —line-control; line-control |
| GLIBC-tcflow | tcflow | — | — | documented | [glibc catalog](./overview.md) | —line-control; line-control |
| GLIBC-tcflush | tcflush | — | — | documented | [glibc catalog](./overview.md) | —line-control; line-control |
| GLIBC-tcgetattr | tcgetattr | — | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-tcsendbreak | tcsendbreak | — | — | documented | [glibc catalog](./overview.md) | —line-control; line-control |
| GLIBC-tcsetattr | tcsetattr | — | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-ttyname | ttyname | `unistd.h` | — | documented | [glibc catalog](./overview.md) | —terminal; terminal |
| GLIBC-ttyname_r | ttyname_r | — | — | documented | [glibc catalog](./overview.md) | —terminal; terminal |
| GLIBC-unlockpt | unlockpt | `stdlib.h` | — | documented | [glibc catalog](./overview.md) | —pty; pty |

### Mathematics

| ID | Function | Header | Exported | Status | Chapter | Notes |
|---|---|---|---|---|---|---|
| GLIBC-acos | acos | `math.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-acosf | acosf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-acosfN | acosfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-acosfNx | acosfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-acosh | acosh | `math.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-acoshf | acoshf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-acoshfN | acoshfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-acoshfNx | acoshfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-acoshl | acoshl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-acosl | acosl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-acospi | acospi | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-acospif | acospif | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-acospifN | acospifN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-acospifNx | acospifNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-acospil | acospil | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-arc4random | arc4random | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-arc4random_buf | arc4random_buf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-arc4random_uniform | arc4random_uniform | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-asin | asin | `math.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-asinf | asinf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-asinfN | asinfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-asinfNx | asinfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-asinh | asinh | `math.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-asinhf | asinhf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-asinhfN | asinhfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-asinhfNx | asinhfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-asinhl | asinhl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-asinl | asinl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-asinpi | asinpi | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-asinpif | asinpif | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-asinpifN | asinpifN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-asinpifNx | asinpifNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-asinpil | asinpil | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-atan | atan | `math.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-atan2 | atan2 | `math.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-atan2f | atan2f | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-atan2fN | atan2fN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-atan2fNx | atan2fNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-atan2l | atan2l | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-atan2pi | atan2pi | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-atan2pif | atan2pif | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-atan2pifN | atan2pifN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-atan2pifNx | atan2pifNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-atan2pil | atan2pil | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-atanf | atanf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-atanfN | atanfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-atanfNx | atanfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-atanh | atanh | `math.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-atanhf | atanhf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-atanhfN | atanhfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-atanhfNx | atanhfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-atanhl | atanhl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-atanl | atanl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-atanpi | atanpi | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-atanpif | atanpif | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-atanpifN | atanpifN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-atanpifNx | atanpifNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-atanpil | atanpil | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-cacos | cacos | `complex.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-cacosf | cacosf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-cacosfN | cacosfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-cacosfNx | cacosfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-cacosh | cacosh | `complex.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-cacoshf | cacoshf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-cacoshfN | cacoshfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-cacoshfNx | cacoshfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-cacoshl | cacoshl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-cacosl | cacosl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-casin | casin | `complex.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-casinf | casinf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-casinfN | casinfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-casinfNx | casinfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-casinh | casinh | `complex.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-casinhf | casinhf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-casinhfN | casinhfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-casinhfNx | casinhfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-casinhl | casinhl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-casinl | casinl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-catan | catan | `complex.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-catanf | catanf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-catanfN | catanfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-catanfNx | catanfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-catanh | catanh | `complex.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-catanhf | catanhf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-catanhfN | catanhfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-catanhfNx | catanhfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-catanhl | catanhl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-catanl | catanl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-cbrt | cbrt | `math.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-cbrtf | cbrtf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-cbrtfN | cbrtfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-cbrtfNx | cbrtfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-cbrtl | cbrtl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-ccos | ccos | `complex.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-ccosf | ccosf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-ccosfN | ccosfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-ccosfNx | ccosfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-ccosh | ccosh | `complex.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-ccoshf | ccoshf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-ccoshfN | ccoshfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-ccoshfNx | ccoshfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-ccoshl | ccoshl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-ccosl | ccosl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-cexp | cexp | `complex.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-cexpf | cexpf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-cexpfN | cexpfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-cexpfNx | cexpfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-cexpl | cexpl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-clog | clog | `complex.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-clog10 | clog10 | `complex.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-clog10f | clog10f | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-clog10fN | clog10fN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-clog10fNx | clog10fNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-clog10l | clog10l | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-clogf | clogf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-clogfN | clogfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-clogfNx | clogfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-clogl | clogl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-compoundn | compoundn | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-compoundnf | compoundnf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-compoundnfN | compoundnfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-compoundnfNx | compoundnfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-compoundnl | compoundnl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-cos | cos | `math.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-cosf | cosf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-cosfN | cosfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-cosfNx | cosfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-cosh | cosh | `math.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-coshf | coshf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-coshfN | coshfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-coshfNx | coshfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-coshl | coshl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-cosl | cosl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-cospi | cospi | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-cospif | cospif | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-cospifN | cospifN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-cospifNx | cospifNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-cospil | cospil | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-cpow | cpow | `complex.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-cpowf | cpowf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-cpowfN | cpowfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-cpowfNx | cpowfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-cpowl | cpowl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-csin | csin | `complex.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-csinf | csinf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-csinfN | csinfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-csinfNx | csinfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-csinh | csinh | `complex.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-csinhf | csinhf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-csinhfN | csinhfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-csinhfNx | csinhfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-csinhl | csinhl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-csinl | csinl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-csqrt | csqrt | `complex.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-csqrtf | csqrtf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-csqrtfN | csqrtfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-csqrtfNx | csqrtfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-csqrtl | csqrtl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-ctan | ctan | `complex.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-ctanf | ctanf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-ctanfN | ctanfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-ctanfNx | ctanfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-ctanh | ctanh | `complex.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-ctanhf | ctanhf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-ctanhfN | ctanhfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-ctanhfNx | ctanhfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-ctanhl | ctanhl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-ctanl | ctanl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-drand48 | drand48 | `stdlib.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-drand48_r | drand48_r | `stdlib.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-erand48 | erand48 | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-erand48_r | erand48_r | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-erf | erf | `math.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-erfc | erfc | `math.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-erfcf | erfcf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-erfcfN | erfcfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-erfcfNx | erfcfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-erfcl | erfcl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-erff | erff | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-erffN | erffN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-erffNx | erffNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-erfl | erfl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-exp | exp | `math.h` | GLIBC_2.2.5 | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-exp10 | exp10 | `math.h` | GLIBC_2.2.5 | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-exp10f | exp10f | — | GLIBC_2.2.5 | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-exp10fN | exp10fN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-exp10fNx | exp10fNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-exp10l | exp10l | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-exp10m1 | exp10m1 | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-exp10m1f | exp10m1f | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-exp10m1fN | exp10m1fN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-exp10m1fNx | exp10m1fNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-exp10m1l | exp10m1l | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-exp2 | exp2 | `math.h` | GLIBC_2.2.5 | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-exp2f | exp2f | — | GLIBC_2.2.5 | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-exp2fN | exp2fN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-exp2fNx | exp2fNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-exp2l | exp2l | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-exp2m1 | exp2m1 | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-exp2m1f | exp2m1f | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-exp2m1fN | exp2m1fN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-exp2m1fNx | exp2m1fNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-exp2m1l | exp2m1l | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-expf | expf | — | GLIBC_2.2.5 | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-expfN | expfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-expfNx | expfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-expl | expl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-expm1 | expm1 | `math.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-expm1f | expm1f | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-expm1fN | expm1fN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-expm1fNx | expm1fNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-expm1l | expm1l | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-gamma | gamma | `math.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-gammaf | gammaf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-gammal | gammal | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-hypot | hypot | `math.h` | GLIBC_2.2.5 | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-hypotf | hypotf | — | GLIBC_2.2.5 | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-hypotfN | hypotfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-hypotfNx | hypotfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-hypotl | hypotl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-ilogb | ilogb | `math.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-ilogbf | ilogbf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-ilogbfN | ilogbfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-ilogbfNx | ilogbfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-ilogbl | ilogbl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-initstate | initstate | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-initstate_r | initstate_r | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-j0 | j0 | `math.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-j0f | j0f | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-j0fN | j0fN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-j0fNx | j0fNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-j0l | j0l | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-j1 | j1 | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-j1f | j1f | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-j1fN | j1fN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-j1fNx | j1fNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-j1l | j1l | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-jn | jn | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-jnf | jnf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-jnfN | jnfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-jnfNx | jnfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-jnl | jnl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-jrand48 | jrand48 | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-jrand48_r | jrand48_r | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-lcong48 | lcong48 | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-lcong48_r | lcong48_r | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-lgamma | lgamma | `math.h` | GLIBC_2.2.5 | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-lgamma_r | lgamma_r | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-lgammaf | lgammaf | — | GLIBC_2.2.5 | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-lgammaf_r | lgammaf_r | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-lgammafN | lgammafN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-lgammafN_r | lgammafN_r | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-lgammafNx | lgammafNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-lgammafNx_r | lgammafNx_r | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-lgammal | lgammal | — | GLIBC_2.2.5 | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-lgammal_r | lgammal_r | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-llogb | llogb | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-llogbf | llogbf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-llogbfN | llogbfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-llogbfNx | llogbfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-llogbl | llogbl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-log | log | `math.h` | GLIBC_2.2.5 | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-log10 | log10 | `math.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-log10f | log10f | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-log10fN | log10fN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-log10fNx | log10fNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-log10l | log10l | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-log10p1 | log10p1 | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-log10p1f | log10p1f | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-log10p1fN | log10p1fN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-log10p1fNx | log10p1fNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-log10p1l | log10p1l | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-log1p | log1p | `math.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-log1pf | log1pf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-log1pfN | log1pfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-log1pfNx | log1pfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-log1pl | log1pl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-log2 | log2 | `math.h` | GLIBC_2.2.5 | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-log2f | log2f | — | GLIBC_2.2.5 | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-log2fN | log2fN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-log2fNx | log2fNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-log2l | log2l | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-log2p1 | log2p1 | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-log2p1f | log2p1f | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-log2p1fN | log2p1fN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-log2p1fNx | log2p1fNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-log2p1l | log2p1l | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-logb | logb | `math.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-logbf | logbf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-logbfN | logbfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-logbfNx | logbfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-logbl | logbl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-logf | logf | — | GLIBC_2.2.5 | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-logfN | logfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-logfNx | logfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-logl | logl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-logp1 | logp1 | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-logp1f | logp1f | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-logp1fN | logp1fN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-logp1fNx | logp1fNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-logp1l | logp1l | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-lrand48 | lrand48 | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-lrand48_r | lrand48_r | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-mrand48 | mrand48 | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-mrand48_r | mrand48_r | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-nrand48 | nrand48 | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-nrand48_r | nrand48_r | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-pow | pow | `math.h` | GLIBC_2.2.5 | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-powf | powf | — | GLIBC_2.2.5 | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-powfN | powfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-powfNx | powfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-powl | powl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-pown | pown | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-pownf | pownf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-pownfN | pownfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-pownfNx | pownfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-pownl | pownl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-powr | powr | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-powrf | powrf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-powrfN | powrfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-powrfNx | powrfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-powrl | powrl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-rand | rand | `stdlib.h` | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-rand_r | rand_r | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-random | random | `stdlib.h` | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-random_r | random_r | `stdlib.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-rootn | rootn | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-rootnf | rootnf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-rootnfN | rootnfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-rootnfNx | rootnfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-rootnl | rootnl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-rsqrt | rsqrt | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-rsqrtf | rsqrtf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-rsqrtfN | rsqrtfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-rsqrtfNx | rsqrtfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-rsqrtl | rsqrtl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-seed48 | seed48 | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-seed48_r | seed48_r | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-setstate | setstate | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-setstate_r | setstate_r | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-sin | sin | `math.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-sincos | sincos | `math.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-sincosf | sincosf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-sincosfN | sincosfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-sincosfNx | sincosfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-sincosl | sincosl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-sinf | sinf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-sinfN | sinfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-sinfNx | sinfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-sinh | sinh | `math.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-sinhf | sinhf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-sinhfN | sinhfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-sinhfNx | sinhfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-sinhl | sinhl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-sinl | sinl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-sinpi | sinpi | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-sinpif | sinpif | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-sinpifN | sinpifN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-sinpifNx | sinpifNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-sinpil | sinpil | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-sqrt | sqrt | `math.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-sqrtf | sqrtf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-sqrtfN | sqrtfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-sqrtfNx | sqrtfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-sqrtl | sqrtl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-srand | srand | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-srand48 | srand48 | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-srand48_r | srand48_r | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-srandom | srandom | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-srandom_r | srandom_r | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-tan | tan | `math.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-tanf | tanf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-tanfN | tanfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-tanfNx | tanfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-tanh | tanh | `math.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-tanhf | tanhf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-tanhfN | tanhfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-tanhfNx | tanhfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-tanhl | tanhl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-tanl | tanl | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-tanpi | tanpi | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-tanpif | tanpif | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-tanpifN | tanpifN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-tanpifNx | tanpifNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-tanpil | tanpil | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-tgamma | tgamma | `math.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-tgammaf | tgammaf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-tgammafN | tgammafN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-tgammafNx | tgammafNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-tgammal | tgammal | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-y0 | y0 | `math.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-y0f | y0f | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-y0fN | y0fN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-y0fNx | y0fNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-y0l | y0l | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-y1 | y1 | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-y1f | y1f | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-y1fN | y1fN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-y1fNx | y1fNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-y1l | y1l | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-yn | yn | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-ynf | ynf | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-ynfN | ynfN | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-ynfNx | ynfNx | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-ynl | ynl | — | — | not-started | [glibc catalog](./overview.md) | — |

### Message Translation

| ID | Function | Header | Exported | Status | Chapter | Notes |
|---|---|---|---|---|---|---|
| GLIBC-bind_textdomain_codeset | bind_textdomain_codeset | — | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-bindtextdomain | bindtextdomain | — | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-catclose | catclose | — | — | documented | [glibc catalog](./overview.md) | —catgets; catgets |
| GLIBC-catgets | catgets | `nl_types.h` | — | documented | [glibc catalog](./overview.md) | —catgets; catgets |
| GLIBC-catopen | catopen | `nl_types.h` | — | documented | [glibc catalog](./overview.md) | —catgets; catgets |
| GLIBC-dcgettext | dcgettext | — | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-dcngettext | dcngettext | — | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-dgettext | dgettext | — | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-dngettext | dngettext | — | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-gettext | gettext | — | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-ngettext | ngettext | — | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-textdomain | textdomain | — | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |

### Non-Local Exits

| ID | Function | Header | Exported | Status | Chapter | Notes |
|---|---|---|---|---|---|---|
| GLIBC-getcontext | getcontext | `ucontext.h` | — | documented | [glibc catalog](./overview.md) | —ucontext; ucontext |
| GLIBC-longjmp | longjmp | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-makecontext | makecontext | `ucontext.h` | — | documented | [glibc catalog](./overview.md) | —ucontext; ucontext |
| GLIBC-setcontext | setcontext | — | — | documented | [glibc catalog](./overview.md) | —ucontext; ucontext |
| GLIBC-siglongjmp | siglongjmp | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-sigsetjmp | sigsetjmp | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-swapcontext | swapcontext | — | — | documented | [glibc catalog](./overview.md) | —ucontext; ucontext |

### Pattern Matching

| ID | Function | Header | Exported | Status | Chapter | Notes |
|---|---|---|---|---|---|---|
| GLIBC-fnmatch | fnmatch | `fnmatch.h` | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-glob | glob | `glob.h` | GLIBC_2.2.5 | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-glob64 | glob64 | — | GLIBC_2.2.5 | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-globfree | globfree | — | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-globfree64 | globfree64 | — | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-regcomp | regcomp | — | — | documented | [glibc catalog](./overview.md) | —regex; regex |
| GLIBC-regerror | regerror | — | — | documented | [glibc catalog](./overview.md) | —regex; regex |
| GLIBC-regexec | regexec | — | GLIBC_2.2.5 | documented | [glibc catalog](./overview.md) | —regex; regex |
| GLIBC-regfree | regfree | — | — | documented | [glibc catalog](./overview.md) | —regex; regex |
| GLIBC-wordexp | wordexp | `wordexp.h` | — | documented | [glibc catalog](./overview.md) | —regex/wordexp; regex/wordexp |
| GLIBC-wordfree | wordfree | — | — | documented | [glibc catalog](./overview.md) | —regex/wordexp; regex/wordexp |

### Pipes and FIFOs

| ID | Function | Header | Exported | Status | Chapter | Notes |
|---|---|---|---|---|---|---|
| GLIBC-mkfifo | mkfifo | `sys/types.h` | — | documented | [glibc catalog](./overview.md) | —pipe/pipe2; pipe/pipe2 |
| GLIBC-pclose | pclose | — | — | documented | [glibc catalog](./overview.md) | —popen/pclose; popen/pclose |
| GLIBC-pipe | pipe | — | — | documented | [glibc catalog](./overview.md) | —pipe/pipe2; pipe/pipe2 |
| GLIBC-popen | popen | `stdio.h` | — | documented | [glibc catalog](./overview.md) | —popen/pclose; popen/pclose |

### Processes

| ID | Function | Header | Exported | Status | Chapter | Notes |
|---|---|---|---|---|---|---|
| GLIBC-_Fork | _Fork | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-execl | execl | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-execle | execle | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-execlp | execlp | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-execv | execv | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-execve | execve | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-execvp | execvp | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-fexecve | fexecve | `unistd.h` | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-fork | fork | — | — | documented | [glibc catalog](./overview.md) | —full; full |
| GLIBC-getpid | getpid | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-getppid | getppid | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-gettid | gettid | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-pidfd_getpid | pidfd_getpid | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-pthread_gettid_np | pthread_gettid_np | — | — | source-limited | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-system | system | `stdlib.h` | — | documented | [glibc catalog](./overview.md) | —full; full |
| GLIBC-vfork | vfork | — | — | documented | [glibc catalog](./overview.md) | —full; full |
| GLIBC-wait | wait | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-wait3 | wait3 | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-wait4 | wait4 | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-waitpid | waitpid | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |

### Resource Usage And Limitation

| ID | Function | Header | Exported | Status | Chapter | Notes |
|---|---|---|---|---|---|---|
| GLIBC-get_avphys_pages | get_avphys_pages | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-get_nprocs | get_nprocs | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-get_nprocs_conf | get_nprocs_conf | `sys/sysinfo.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-get_phys_pages | get_phys_pages | `sys/sysinfo.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-getcpu | getcpu | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-getloadavg | getloadavg | `stdlib.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-getpagesize | getpagesize | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-getpriority | getpriority | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-getrlimit | getrlimit | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-getrlimit64 | getrlimit64 | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-getrusage | getrusage | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-nice | nice | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-sched_get_priority_max | sched_get_priority_max | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-sched_get_priority_min | sched_get_priority_min | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-sched_getaffinity | sched_getaffinity | — | GLIBC_2.3.3 | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-sched_getattr | sched_getattr | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-sched_getcpu | sched_getcpu | `sched.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-sched_getparam | sched_getparam | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-sched_getscheduler | sched_getscheduler | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-sched_rr_get_interval | sched_rr_get_interval | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-sched_setaffinity | sched_setaffinity | — | GLIBC_2.3.3 | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-sched_setattr | sched_setattr | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-sched_setparam | sched_setparam | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-sched_setscheduler | sched_setscheduler | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-sched_yield | sched_yield | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-setpriority | setpriority | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-setrlimit | setrlimit | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-setrlimit64 | setrlimit64 | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-ulimit | ulimit | `ulimit.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-vlimit | vlimit | — | — | not-started | [glibc catalog](./overview.md) | — |

### Searching and Sorting

| ID | Function | Header | Exported | Status | Chapter | Notes |
|---|---|---|---|---|---|---|
| GLIBC-bsearch | bsearch | `stdlib.h` | — | documented | [glibc catalog](./overview.md) | —full; full |
| GLIBC-hcreate | hcreate | — | — | documented | [glibc catalog](./overview.md) | —hash; hash |
| GLIBC-hcreate_r | hcreate_r | — | — | documented | [glibc catalog](./overview.md) | —hash; hash |
| GLIBC-hdestroy | hdestroy | — | — | documented | [glibc catalog](./overview.md) | —hash; hash |
| GLIBC-hdestroy_r | hdestroy_r | — | — | documented | [glibc catalog](./overview.md) | —hash; hash |
| GLIBC-hsearch | hsearch | `search.h` | — | documented | [glibc catalog](./overview.md) | —hash; hash |
| GLIBC-hsearch_r | hsearch_r | — | — | documented | [glibc catalog](./overview.md) | —hash; hash |
| GLIBC-lfind | lfind | — | — | documented | [glibc catalog](./overview.md) | —linear; linear |
| GLIBC-lsearch | lsearch | `search.h` | — | documented | [glibc catalog](./overview.md) | —linear; linear |
| GLIBC-qsort | qsort | `stdlib.h` | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-tdelete | tdelete | — | — | documented | [glibc catalog](./overview.md) | —tree; tree |
| GLIBC-tdestroy | tdestroy | — | — | documented | [glibc catalog](./overview.md) | —tree; tree |
| GLIBC-tfind | tfind | — | — | documented | [glibc catalog](./overview.md) | —tree; tree |
| GLIBC-tsearch | tsearch | `search.h` | — | documented | [glibc catalog](./overview.md) | —tree; tree |
| GLIBC-twalk | twalk | — | — | documented | [glibc catalog](./overview.md) | —tree; tree |
| GLIBC-twalk_r | twalk_r | — | — | documented | [glibc catalog](./overview.md) | —tree; tree |

### Signal Handling

| ID | Function | Header | Exported | Status | Chapter | Notes |
|---|---|---|---|---|---|---|
| GLIBC-gsignal | gsignal | `signal.h` | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-kill | kill | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-killpg | killpg | `signal.h` | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-pause | pause | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-psignal | psignal | `signal.h` | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-raise | raise | `signal.h` | — | documented | [glibc catalog](./overview.md) | —full; full |
| GLIBC-sigabbrev_np | sigabbrev_np | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-sigaction | sigaction | — | — | documented | [glibc catalog](./overview.md) | —full; full |
| GLIBC-sigaddset | sigaddset | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-sigaltstack | sigaltstack | — | — | documented | [glibc catalog](./overview.md) | —full; full |
| GLIBC-sigblock | sigblock | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-sigdelset | sigdelset | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-sigdescr_np | sigdescr_np | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-sigemptyset | sigemptyset | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-sigfillset | sigfillset | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-siginterrupt | siginterrupt | `signal.h` | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-sigismember | sigismember | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-signal | signal | — | — | documented | [glibc catalog](./overview.md) | —full; full |
| GLIBC-sigpause | sigpause | `signal.h` | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-sigpending | sigpending | — | — | documented | [glibc catalog](./overview.md) | —full; full |
| GLIBC-sigprocmask | sigprocmask | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-sigsetmask | sigsetmask | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-sigstack | sigstack | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-sigsuspend | sigsuspend | — | — | documented | [glibc catalog](./overview.md) | —full; full |
| GLIBC-ssignal | ssignal | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-strsignal | strsignal | `string.h` | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-sysv_signal | sysv_signal | `signal.h` | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-tgkill | tgkill | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |

### Sockets

| ID | Function | Header | Exported | Status | Chapter | Notes |
|---|---|---|---|---|---|---|
| GLIBC-accept | accept | — | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-bind | bind | — | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-connect | connect | — | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-endhostent | endhostent | — | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-endnetent | endnetent | — | — | documented | [glibc catalog](./overview.md) | —networks(5); networks(5) |
| GLIBC-endprotoent | endprotoent | — | — | documented | [glibc catalog](./overview.md) | —protocols(5); protocols(5) |
| GLIBC-endservent | endservent | — | — | documented | [glibc catalog](./overview.md) | —services(5); services(5) |
| GLIBC-gethostbyaddr | gethostbyaddr | — | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-gethostbyaddr_r | gethostbyaddr_r | — | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-gethostbyname | gethostbyname | `netdb.h` | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-gethostbyname2 | gethostbyname2 | — | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-gethostbyname2_r | gethostbyname2_r | — | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-gethostbyname_r | gethostbyname_r | — | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-gethostent | gethostent | — | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-getnetbyaddr | getnetbyaddr | — | — | documented | [glibc catalog](./overview.md) | —netdb; netdb |
| GLIBC-getnetbyname | getnetbyname | — | — | documented | [glibc catalog](./overview.md) | —netdb; netdb |
| GLIBC-getnetent | getnetent | `netdb.h` | — | documented | [glibc catalog](./overview.md) | —netdb; netdb |
| GLIBC-getpeername | getpeername | — | — | documented | [glibc catalog](./overview.md) | —netdb; netdb |
| GLIBC-getprotobyname | getprotobyname | — | — | documented | [glibc catalog](./overview.md) | —netdb; netdb |
| GLIBC-getprotobynumber | getprotobynumber | — | — | documented | [glibc catalog](./overview.md) | —netdb; netdb |
| GLIBC-getprotoent | getprotoent | `netdb.h` | — | documented | [glibc catalog](./overview.md) | —netdb; netdb |
| GLIBC-getservbyname | getservbyname | — | — | documented | [glibc catalog](./overview.md) | —netdb; netdb |
| GLIBC-getservbyport | getservbyport | — | — | documented | [glibc catalog](./overview.md) | —netdb; netdb |
| GLIBC-getservent | getservent | `netdb.h` | — | documented | [glibc catalog](./overview.md) | —netdb; netdb |
| GLIBC-getsockname | getsockname | — | — | documented | [glibc catalog](./overview.md) | —netdb; netdb |
| GLIBC-getsockopt | getsockopt | — | — | documented | [glibc catalog](./overview.md) | —netdb; netdb |
| GLIBC-htonl | htonl | — | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-htons | htons | — | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-if_freenameindex | if_freenameindex | — | — | documented | [glibc catalog](./overview.md) | —netdb; netdb |
| GLIBC-if_indextoname | if_indextoname | — | — | documented | [glibc catalog](./overview.md) | —netdb; netdb |
| GLIBC-if_nameindex | if_nameindex | `net/if.h` | — | documented | [glibc catalog](./overview.md) | —netdb; netdb |
| GLIBC-if_nametoindex | if_nametoindex | `net/if.h` | — | documented | [glibc catalog](./overview.md) | —netdb; netdb |
| GLIBC-inet_addr | inet_addr | — | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-inet_aton | inet_aton | — | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-inet_lnaof | inet_lnaof | — | — | documented | [glibc catalog](./overview.md) | —classful; classful |
| GLIBC-inet_makeaddr | inet_makeaddr | — | — | documented | [glibc catalog](./overview.md) | —classful; classful |
| GLIBC-inet_netof | inet_netof | — | — | documented | [glibc catalog](./overview.md) | —classful; classful |
| GLIBC-inet_network | inet_network | — | — | documented | [glibc catalog](./overview.md) | —classful; classful |
| GLIBC-inet_ntoa | inet_ntoa | — | — | documented | [glibc catalog](./overview.md) | —static-buffer; static-buffer |
| GLIBC-inet_ntop | inet_ntop | `arpa/inet.h` | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-inet_pton | inet_pton | `arpa/inet.h` | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-listen | listen | — | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-ntohl | ntohl | — | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-ntohs | ntohs | — | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-recv | recv | — | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-recvfrom | recvfrom | — | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-recvmsg | recvmsg | — | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-send | send | — | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-sendmsg | sendmsg | — | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-sendto | sendto | — | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-sethostent | sethostent | — | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-setnetent | setnetent | — | — | documented | [glibc catalog](./overview.md) | —netdb; netdb |
| GLIBC-setprotoent | setprotoent | — | — | documented | [glibc catalog](./overview.md) | —netdb; netdb |
| GLIBC-setservent | setservent | — | — | documented | [glibc catalog](./overview.md) | —netdb; netdb |
| GLIBC-setsockopt | setsockopt | — | — | documented | [glibc catalog](./overview.md) | —netdb; netdb |
| GLIBC-shutdown | shutdown | — | — | documented | [glibc catalog](./overview.md) | —netdb; netdb |
| GLIBC-socket | socket | — | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-socketpair | socketpair | — | — | documented | [glibc catalog](./overview.md) | —FULL; FULL |

### String and Array Utilities

| ID | Function | Header | Exported | Status | Chapter | Notes |
|---|---|---|---|---|---|---|
| GLIBC-a64l | a64l | `stdlib.h` | — | documented | [glibc catalog](./overview.md) | —string.h; string.h |
| GLIBC-argz_add | argz_add | `argz.h` | — | documented | [glibc catalog](./overview.md) | —string.h; string.h |
| GLIBC-argz_add_sep | argz_add_sep | — | — | documented | [glibc catalog](./overview.md) | —string.h; string.h |
| GLIBC-argz_append | argz_append | — | — | documented | [glibc catalog](./overview.md) | —string.h; string.h |
| GLIBC-argz_count | argz_count | — | — | documented | [glibc catalog](./overview.md) | —string.h; string.h |
| GLIBC-argz_create | argz_create | — | — | documented | [glibc catalog](./overview.md) | —string.h; string.h |
| GLIBC-argz_create_sep | argz_create_sep | — | — | documented | [glibc catalog](./overview.md) | —string.h; string.h |
| GLIBC-argz_delete | argz_delete | — | — | documented | [glibc catalog](./overview.md) | —string.h; string.h |
| GLIBC-argz_extract | argz_extract | — | — | documented | [glibc catalog](./overview.md) | —string.h; string.h |
| GLIBC-argz_insert | argz_insert | — | — | documented | [glibc catalog](./overview.md) | —string.h; string.h |
| GLIBC-argz_next | argz_next | — | — | documented | [glibc catalog](./overview.md) | —string.h; string.h |
| GLIBC-argz_replace | argz_replace | — | — | documented | [glibc catalog](./overview.md) | —string.h; string.h |
| GLIBC-argz_stringify | argz_stringify | — | — | documented | [glibc catalog](./overview.md) | —string.h; string.h |
| GLIBC-basename | basename | `libgen.h` | — | documented | [glibc catalog](./overview.md) | —string.h; string.h |
| GLIBC-bcmp | bcmp | `strings.h` | — | documented | [glibc catalog](./overview.md) | —string.h; string.h |
| GLIBC-bcopy | bcopy | `strings.h` | — | documented | [glibc catalog](./overview.md) | —string.h; string.h |
| GLIBC-bzero | bzero | `strings.h` | — | documented | [glibc catalog](./overview.md) | —string.h; string.h |
| GLIBC-dirname | dirname | — | — | documented | [glibc catalog](./overview.md) | —string.h; string.h |
| GLIBC-envz_add | envz_add | `envz.h` | — | documented | [glibc catalog](./overview.md) | —string.h; string.h |
| GLIBC-envz_entry | envz_entry | — | — | documented | [glibc catalog](./overview.md) | —string.h; string.h |
| GLIBC-envz_get | envz_get | — | — | documented | [glibc catalog](./overview.md) | —string.h; string.h |
| GLIBC-envz_merge | envz_merge | — | — | documented | [glibc catalog](./overview.md) | —string.h; string.h |
| GLIBC-envz_remove | envz_remove | — | — | documented | [glibc catalog](./overview.md) | —string.h; string.h |
| GLIBC-envz_strip | envz_strip | — | — | documented | [glibc catalog](./overview.md) | —string.h; string.h |
| GLIBC-explicit_bzero | explicit_bzero | — | — | documented | [glibc catalog](./overview.md) | —string.h; string.h |
| GLIBC-index | index | `strings.h` | — | documented | [glibc catalog](./overview.md) | —string.h; string.h |
| GLIBC-l64a | l64a | — | — | documented | [glibc catalog](./overview.md) | —string.h; string.h |
| GLIBC-memccpy | memccpy | `string.h` | — | documented | [glibc catalog](./overview.md) | —string.h; string.h |
| GLIBC-memchr | memchr | `string.h` | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-memcmp | memcmp | `string.h` | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-memcpy | memcpy | `string.h` | GLIBC_2.2.5 | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-memfrob | memfrob | `string.h` | — | documented | [glibc catalog](./overview.md) | —string.h; string.h |
| GLIBC-memmem | memmem | `string.h` | — | documented | [glibc catalog](./overview.md) | —string.h; string.h |
| GLIBC-memmove | memmove | `string.h` | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-mempcpy | mempcpy | `string.h` | — | documented | [glibc catalog](./overview.md) | —string.h; string.h |
| GLIBC-memrchr | memrchr | — | — | documented | [glibc catalog](./overview.md) | —string.h; string.h |
| GLIBC-memset | memset | `string.h` | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-memset_explicit | memset_explicit | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-rawmemchr | rawmemchr | — | — | documented | [glibc catalog](./overview.md) | —string.h; string.h |
| GLIBC-rindex | rindex | — | — | documented | [glibc catalog](./overview.md) | —string.h; string.h |
| GLIBC-stpcpy | stpcpy | `string.h` | — | documented | [glibc catalog](./overview.md) | —string.h; string.h |
| GLIBC-stpncpy | stpncpy | `string.h` | — | documented | [glibc catalog](./overview.md) | —string.h; string.h |
| GLIBC-strcasecmp | strcasecmp | `strings.h` | — | documented | [glibc catalog](./overview.md) | —string.h; string.h |
| GLIBC-strcasestr | strcasestr | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-strcat | strcat | `string.h` | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-strchr | strchr | `string.h` | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-strchrnul | strchrnul | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-strcmp | strcmp | `string.h` | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-strcoll | strcoll | `string.h` | — | documented | [glibc catalog](./overview.md) | —string.h; string.h |
| GLIBC-strcpy | strcpy | `string.h` | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-strcspn | strcspn | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-strdup | strdup | `string.h` | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-strfry | strfry | `string.h` | — | documented | [glibc catalog](./overview.md) | —string.h; string.h |
| GLIBC-strlcat | strlcat | — | — | documented | [glibc catalog](./overview.md) | —string.h; string.h |
| GLIBC-strlcpy | strlcpy | — | — | documented | [glibc catalog](./overview.md) | —string.h; string.h |
| GLIBC-strlen | strlen | `string.h` | — | documented | [glibc catalog](./overview.md) | —full; full |
| GLIBC-strncasecmp | strncasecmp | — | — | documented | [glibc catalog](./overview.md) | —string.h; string.h |
| GLIBC-strncat | strncat | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-strncmp | strncmp | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-strncpy | strncpy | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-strndup | strndup | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-strnlen | strnlen | `string.h` | — | documented | [glibc catalog](./overview.md) | —string.h; string.h |
| GLIBC-strpbrk | strpbrk | `string.h` | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-strrchr | strrchr | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-strsep | strsep | `string.h` | — | documented | [glibc catalog](./overview.md) | —string.h; string.h |
| GLIBC-strspn | strspn | `string.h` | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-strstr | strstr | `string.h` | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-strtok | strtok | `string.h` | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-strtok_r | strtok_r | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-strverscmp | strverscmp | `string.h` | — | documented | [glibc catalog](./overview.md) | —string.h; string.h |
| GLIBC-strxfrm | strxfrm | `string.h` | — | documented | [glibc catalog](./overview.md) | —string.h; string.h |
| GLIBC-wcpcpy | wcpcpy | `wchar.h` | — | documented | [glibc catalog](./overview.md) | —string.h; string.h |
| GLIBC-wcpncpy | wcpncpy | `wchar.h` | — | documented | [glibc catalog](./overview.md) | —string.h; string.h |
| GLIBC-wcscasecmp | wcscasecmp | `wchar.h` | — | documented | [glibc catalog](./overview.md) | —string.h; string.h |
| GLIBC-wcscat | wcscat | `wchar.h` | — | documented | [glibc catalog](./overview.md) | —string.h; string.h |
| GLIBC-wcschr | wcschr | `wchar.h` | — | documented | [glibc catalog](./overview.md) | —string.h; string.h |
| GLIBC-wcschrnul | wcschrnul | — | — | documented | [glibc catalog](./overview.md) | —string.h; string.h |
| GLIBC-wcscmp | wcscmp | `wchar.h` | — | documented | [glibc catalog](./overview.md) | —string.h; string.h |
| GLIBC-wcscoll | wcscoll | — | — | documented | [glibc catalog](./overview.md) | —string.h; string.h |
| GLIBC-wcscpy | wcscpy | `wchar.h` | — | documented | [glibc catalog](./overview.md) | —string.h; string.h |
| GLIBC-wcscspn | wcscspn | `wchar.h` | — | documented | [glibc catalog](./overview.md) | —string.h; string.h |
| GLIBC-wcsdup | wcsdup | `wchar.h` | — | documented | [glibc catalog](./overview.md) | —string.h; string.h |
| GLIBC-wcslcat | wcslcat | — | — | documented | [glibc catalog](./overview.md) | —string.h; string.h |
| GLIBC-wcslcpy | wcslcpy | — | — | documented | [glibc catalog](./overview.md) | —string.h; string.h |
| GLIBC-wcslen | wcslen | `wchar.h` | — | documented | [glibc catalog](./overview.md) | —string.h; string.h |
| GLIBC-wcsncasecmp | wcsncasecmp | `wchar.h` | — | documented | [glibc catalog](./overview.md) | —string.h; string.h |
| GLIBC-wcsncat | wcsncat | `wchar.h` | — | documented | [glibc catalog](./overview.md) | —string.h; string.h |
| GLIBC-wcsncmp | wcsncmp | `wchar.h` | — | documented | [glibc catalog](./overview.md) | —string.h; string.h |
| GLIBC-wcsncpy | wcsncpy | `wchar.h` | — | documented | [glibc catalog](./overview.md) | —string.h; string.h |
| GLIBC-wcsnlen | wcsnlen | `wchar.h` | — | documented | [glibc catalog](./overview.md) | —string.h; string.h |
| GLIBC-wcspbrk | wcspbrk | `wchar.h` | — | documented | [glibc catalog](./overview.md) | —string.h; string.h |
| GLIBC-wcsrchr | wcsrchr | `wchar.h` | — | documented | [glibc catalog](./overview.md) | —string.h; string.h |
| GLIBC-wcsspn | wcsspn | `wchar.h` | — | documented | [glibc catalog](./overview.md) | —string.h; string.h |
| GLIBC-wcsstr | wcsstr | `wchar.h` | — | documented | [glibc catalog](./overview.md) | —string.h; string.h |
| GLIBC-wcstok | wcstok | `wchar.h` | — | documented | [glibc catalog](./overview.md) | —string.h; string.h |
| GLIBC-wcswcs | wcswcs | — | — | documented | [glibc catalog](./overview.md) | —string.h; string.h |
| GLIBC-wcsxfrm | wcsxfrm | — | — | documented | [glibc catalog](./overview.md) | —string.h; string.h |
| GLIBC-wmemchr | wmemchr | `wchar.h` | — | documented | [glibc catalog](./overview.md) | —string.h; string.h |
| GLIBC-wmemcmp | wmemcmp | `wchar.h` | — | documented | [glibc catalog](./overview.md) | —string.h; string.h |
| GLIBC-wmemcpy | wmemcpy | `wchar.h` | — | documented | [glibc catalog](./overview.md) | —string.h; string.h |
| GLIBC-wmemmove | wmemmove | `wchar.h` | — | documented | [glibc catalog](./overview.md) | —string.h; string.h |
| GLIBC-wmempcpy | wmempcpy | — | — | documented | [glibc catalog](./overview.md) | —string.h; string.h |
| GLIBC-wmemset | wmemset | `wchar.h` | — | documented | [glibc catalog](./overview.md) | —string.h; string.h |

### Syslog

| ID | Function | Header | Exported | Status | Chapter | Notes |
|---|---|---|---|---|---|---|
| GLIBC-closelog | closelog | — | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-openlog | openlog | — | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-setlogmask | setlogmask | `syslog.h` | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-syslog | syslog | `syslog.h` | — | documented | [glibc catalog](./overview.md) | —FULL; FULL |
| GLIBC-vsyslog | vsyslog | — | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |

### System Configuration Parameters

| ID | Function | Header | Exported | Status | Chapter | Notes |
|---|---|---|---|---|---|---|
| GLIBC-confstr | confstr | `unistd.h` | — | documented | [glibc catalog](./overview.md) | —pathconf/confstr; pathconf/confstr |
| GLIBC-fpathconf | fpathconf | `unistd.h` | — | documented | [glibc catalog](./overview.md) | —pathconf/confstr; pathconf/confstr |
| GLIBC-pathconf | pathconf | — | — | documented | [glibc catalog](./overview.md) | —pathconf/confstr; pathconf/confstr |
| GLIBC-sysconf | sysconf | `unistd.h` | — | documented | [glibc catalog](./overview.md) | —FULL; FULL |

### System Management

| ID | Function | Header | Exported | Status | Chapter | Notes |
|---|---|---|---|---|---|---|
| GLIBC-addmntent | addmntent | — | — | documented | [glibc catalog](./overview.md) | —mntent; mntent |
| GLIBC-endfsent | endfsent | — | — | documented | [glibc catalog](./overview.md) | —fstab; fstab |
| GLIBC-endmntent | endmntent | — | — | documented | [glibc catalog](./overview.md) | —mntent; mntent |
| GLIBC-getdomainname | getdomainname | — | — | documented | [glibc catalog](./overview.md) | —host-identification; host-identification |
| GLIBC-getfsent | getfsent | `fstab.h` | — | documented | [glibc catalog](./overview.md) | —fstab; fstab |
| GLIBC-getfsfile | getfsfile | — | — | documented | [glibc catalog](./overview.md) | —fstab; fstab |
| GLIBC-getfsspec | getfsspec | — | — | documented | [glibc catalog](./overview.md) | —fstab; fstab |
| GLIBC-gethostid | gethostid | `unistd.h` | — | documented | [glibc catalog](./overview.md) | —host-identification; host-identification |
| GLIBC-gethostname | gethostname | — | — | documented | [glibc catalog](./overview.md) | —host-identification; host-identification |
| GLIBC-getmntent | getmntent | `stdio.h` | — | documented | [glibc catalog](./overview.md) | —mntent; mntent |
| GLIBC-getmntent_r | getmntent_r | — | — | documented | [glibc catalog](./overview.md) | —mntent; mntent |
| GLIBC-hasmntopt | hasmntopt | — | — | documented | [glibc catalog](./overview.md) | —mntent; mntent |
| GLIBC-mount | mount | — | — | documented | [glibc catalog](./overview.md) | —mount; mount |
| GLIBC-setdomainname | setdomainname | — | — | documented | [glibc catalog](./overview.md) | —host-identification; host-identification |
| GLIBC-setfsent | setfsent | — | — | documented | [glibc catalog](./overview.md) | —fstab; fstab |
| GLIBC-sethostid | sethostid | — | — | documented | [glibc catalog](./overview.md) | —host-identification; host-identification |
| GLIBC-sethostname | sethostname | — | — | documented | [glibc catalog](./overview.md) | —host-identification; host-identification |
| GLIBC-setmntent | setmntent | — | — | documented | [glibc catalog](./overview.md) | —mntent; mntent |
| GLIBC-umount | umount | — | — | documented | [glibc catalog](./overview.md) | —umount; umount |
| GLIBC-umount2 | umount2 | — | — | documented | [glibc catalog](./overview.md) | —umount; umount |
| GLIBC-uname | uname | — | — | documented | [glibc catalog](./overview.md) | —uname; uname |

### The Basic Program/System Interface

| ID | Function | Header | Exported | Status | Chapter | Notes |
|---|---|---|---|---|---|---|
| GLIBC-_exit | _exit | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-_Exit | _Exit | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-abort | abort | `stdlib.h` | — | documented | [glibc catalog](./overview.md) | —full; full |
| GLIBC-atexit | atexit | `stdlib.h` | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-clearenv | clearenv | `stdlib.h` | — | documented | [glibc catalog](./overview.md) | —basic-prog; recap; basic-prog; recap |
| GLIBC-exit | exit | `stdlib.h` | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-getauxval | getauxval | `sys/auxv.h` | — | documented | [glibc catalog](./overview.md) | —basic-prog; recap; basic-prog; recap |
| GLIBC-getenv | getenv | `stdlib.h` | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-getsubopt | getsubopt | `stdlib.h` | — | documented | [glibc catalog](./overview.md) | —basic-prog; recap; basic-prog; recap |
| GLIBC-on_exit | on_exit | `stdlib.h` | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-putenv | putenv | `stdlib.h` | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-secure_getenv | secure_getenv | — | — | documented | [glibc catalog](./overview.md) | —basic-prog; recap; basic-prog; recap |
| GLIBC-setenv | setenv | `stdlib.h` | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-syscall | syscall | — | — | documented | [glibc catalog](./overview.md) | —basic-prog; recap; basic-prog; recap |
| GLIBC-unsetenv | unsetenv | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |

### Threads

| ID | Function | Header | Exported | Status | Chapter | Notes |
|---|---|---|---|---|---|---|
| GLIBC-call_once | call_once | — | GLIBC_2.28 | documented | [glibc catalog](./overview.md) | —C11; C11 |
| GLIBC-cnd_broadcast | cnd_broadcast | — | GLIBC_2.28 | documented | [glibc catalog](./overview.md) | —C11; C11 |
| GLIBC-cnd_destroy | cnd_destroy | — | GLIBC_2.28 | documented | [glibc catalog](./overview.md) | —C11; C11 |
| GLIBC-cnd_init | cnd_init | — | GLIBC_2.28 | documented | [glibc catalog](./overview.md) | —C11; C11 |
| GLIBC-cnd_signal | cnd_signal | — | GLIBC_2.28 | documented | [glibc catalog](./overview.md) | —C11; C11 |
| GLIBC-cnd_timedwait | cnd_timedwait | — | GLIBC_2.28 | documented | [glibc catalog](./overview.md) | —C11; C11 |
| GLIBC-cnd_wait | cnd_wait | — | GLIBC_2.28 | documented | [glibc catalog](./overview.md) | —C11; C11 |
| GLIBC-mtx_destroy | mtx_destroy | — | GLIBC_2.28 | documented | [glibc catalog](./overview.md) | —C11; C11 |
| GLIBC-mtx_init | mtx_init | — | GLIBC_2.28 | documented | [glibc catalog](./overview.md) | —C11; C11 |
| GLIBC-mtx_lock | mtx_lock | — | GLIBC_2.28 | documented | [glibc catalog](./overview.md) | —C11; C11 |
| GLIBC-mtx_timedlock | mtx_timedlock | — | GLIBC_2.28 | documented | [glibc catalog](./overview.md) | —C11; C11 |
| GLIBC-mtx_trylock | mtx_trylock | — | GLIBC_2.28 | documented | [glibc catalog](./overview.md) | —C11; C11 |
| GLIBC-mtx_unlock | mtx_unlock | — | GLIBC_2.28 | documented | [glibc catalog](./overview.md) | —C11; C11 |
| GLIBC-pthread_attr_destroy | pthread_attr_destroy | — | — | documented | [glibc catalog](./overview.md) | —attr; attr |
| GLIBC-pthread_attr_getaffinity_np | pthread_attr_getaffinity_np | — | GLIBC_2.3.4 | documented | [glibc catalog](./overview.md) | —attr; attr |
| GLIBC-pthread_attr_getdetachstate | pthread_attr_getdetachstate | — | — | documented | [glibc catalog](./overview.md) | —attr; attr |
| GLIBC-pthread_attr_getsigmask_np | pthread_attr_getsigmask_np | — | — | documented | [glibc catalog](./overview.md) | —attr; attr |
| GLIBC-pthread_attr_init | pthread_attr_init | `pthread.h` | — | documented | [glibc catalog](./overview.md) | —attr; attr |
| GLIBC-pthread_attr_setaffinity_np | pthread_attr_setaffinity_np | `pthread.h` | GLIBC_2.3.4 | documented | [glibc catalog](./overview.md) | —attr; attr |
| GLIBC-pthread_attr_setdetachstate | pthread_attr_setdetachstate | `pthread.h` | — | documented | [glibc catalog](./overview.md) | —attr; attr |
| GLIBC-pthread_attr_setsigmask_np | pthread_attr_setsigmask_np | `pthread.h` | — | documented | [glibc catalog](./overview.md) | —attr; attr |
| GLIBC-pthread_barrier_destroy | pthread_barrier_destroy | — | GLIBC_2.2.5 | documented | [glibc catalog](./overview.md) | —barrier; barrier |
| GLIBC-pthread_barrier_init | pthread_barrier_init | — | GLIBC_2.2.5 | documented | [glibc catalog](./overview.md) | —barrier; barrier |
| GLIBC-pthread_barrier_wait | pthread_barrier_wait | — | GLIBC_2.2.5 | documented | [glibc catalog](./overview.md) | —barrier; barrier |
| GLIBC-pthread_clockjoin_np | pthread_clockjoin_np | — | GLIBC_2.31 | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-pthread_cond_clockwait | pthread_cond_clockwait | — | GLIBC_2.30 | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-pthread_create | pthread_create | `pthread.h` | GLIBC_2.2.5 | documented | [glibc catalog](./overview.md) | —full; full |
| GLIBC-pthread_detach | pthread_detach | `pthread.h` | GLIBC_2.2.5 | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-pthread_equal | pthread_equal | `pthread.h` | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-pthread_getaffinity_np | pthread_getaffinity_np | — | GLIBC_2.3.4 | documented | [glibc catalog](./overview.md) | —attr; attr |
| GLIBC-pthread_getattr_default_np | pthread_getattr_default_np | `pthread.h` | GLIBC_2.18 | documented | [glibc catalog](./overview.md) | —attr; attr |
| GLIBC-pthread_getcpuclockid | pthread_getcpuclockid | `pthread.h` | GLIBC_2.2.5 | documented | [glibc catalog](./overview.md) | —attr/info; attr/info |
| GLIBC-pthread_getname_np | pthread_getname_np | — | GLIBC_2.12 | documented | [glibc catalog](./overview.md) | —attr/info; attr/info |
| GLIBC-pthread_getspecific | pthread_getspecific | — | GLIBC_2.2.5 | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-pthread_join | pthread_join | `pthread.h` | GLIBC_2.2.5 | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-pthread_key_create | pthread_key_create | — | GLIBC_2.2.5 | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-pthread_key_delete | pthread_key_delete | — | GLIBC_2.2.5 | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-pthread_kill | pthread_kill | `signal.h` | GLIBC_2.2.5 | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-pthread_mutex_clocklock | pthread_mutex_clocklock | — | GLIBC_2.30 | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-pthread_mutex_destroy | pthread_mutex_destroy | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-pthread_mutex_init | pthread_mutex_init | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-pthread_mutex_lock | pthread_mutex_lock | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-pthread_mutex_timedlock | pthread_mutex_timedlock | — | GLIBC_2.2.5 | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-pthread_mutex_trylock | pthread_mutex_trylock | — | GLIBC_2.2.5 | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-pthread_mutex_unlock | pthread_mutex_unlock | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-pthread_mutexattr_destroy | pthread_mutexattr_destroy | — | GLIBC_2.2.5 | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-pthread_mutexattr_gettype | pthread_mutexattr_gettype | — | GLIBC_2.2.5 | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-pthread_mutexattr_init | pthread_mutexattr_init | `pthread.h` | GLIBC_2.2.5 | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-pthread_mutexattr_settype | pthread_mutexattr_settype | — | GLIBC_2.2.5 | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-pthread_once | pthread_once | — | GLIBC_2.2.5 | documented | [glibc catalog](./overview.md) | —full; full |
| GLIBC-pthread_rwlock_clockrdlock | pthread_rwlock_clockrdlock | — | GLIBC_2.30 | documented | [glibc catalog](./overview.md) | —rwlock; rwlock |
| GLIBC-pthread_rwlock_clockwrlock | pthread_rwlock_clockwrlock | — | GLIBC_2.30 | documented | [glibc catalog](./overview.md) | —rwlock; rwlock |
| GLIBC-pthread_self | pthread_self | `pthread.h` | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-pthread_setaffinity_np | pthread_setaffinity_np | `pthread.h` | GLIBC_2.3.4 | documented | [glibc catalog](./overview.md) | —attr; attr |
| GLIBC-pthread_setattr_default_np | pthread_setattr_default_np | — | GLIBC_2.18 | documented | [glibc catalog](./overview.md) | —attr; attr |
| GLIBC-pthread_setname_np | pthread_setname_np | `pthread.h` | GLIBC_2.12 | documented | [glibc catalog](./overview.md) | —attr/info; attr/info |
| GLIBC-pthread_setspecific | pthread_setspecific | — | GLIBC_2.2.5 | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-pthread_sigmask | pthread_sigmask | `signal.h` | GLIBC_2.2.5 | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-pthread_spin_destroy | pthread_spin_destroy | — | GLIBC_2.2.5 | documented | [glibc catalog](./overview.md) | —spinlock; spinlock |
| GLIBC-pthread_spin_init | pthread_spin_init | `pthread.h` | GLIBC_2.2.5 | documented | [glibc catalog](./overview.md) | —spinlock; spinlock |
| GLIBC-pthread_spin_lock | pthread_spin_lock | `pthread.h` | GLIBC_2.2.5 | documented | [glibc catalog](./overview.md) | —spinlock; spinlock |
| GLIBC-pthread_spin_trylock | pthread_spin_trylock | — | GLIBC_2.2.5 | documented | [glibc catalog](./overview.md) | —spinlock; spinlock |
| GLIBC-pthread_spin_unlock | pthread_spin_unlock | — | GLIBC_2.2.5 | documented | [glibc catalog](./overview.md) | —spinlock; spinlock |
| GLIBC-pthread_timedjoin_np | pthread_timedjoin_np | — | GLIBC_2.3.3 | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-pthread_tryjoin_np | pthread_tryjoin_np | `pthread.h` | GLIBC_2.3.3 | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-sem_clockwait | sem_clockwait | — | GLIBC_2.30 | documented | [glibc catalog](./overview.md) | —semaphore; semaphore |
| GLIBC-sem_close | sem_close | `semaphore.h` | GLIBC_2.2.5 | documented | [glibc catalog](./overview.md) | —semaphore; semaphore |
| GLIBC-sem_destroy | sem_destroy | `semaphore.h` | GLIBC_2.2.5 | documented | [glibc catalog](./overview.md) | —semaphore; semaphore |
| GLIBC-sem_getvalue | sem_getvalue | `semaphore.h` | GLIBC_2.2.5 | documented | [glibc catalog](./overview.md) | —semaphore; semaphore |
| GLIBC-sem_init | sem_init | `semaphore.h` | GLIBC_2.2.5 | documented | [glibc catalog](./overview.md) | —semaphore; semaphore |
| GLIBC-sem_open | sem_open | `fcntl.h` | GLIBC_2.2.5 | documented | [glibc catalog](./overview.md) | —semaphore; semaphore |
| GLIBC-sem_post | sem_post | `semaphore.h` | GLIBC_2.2.5 | documented | [glibc catalog](./overview.md) | —semaphore; semaphore |
| GLIBC-sem_timedwait | sem_timedwait | — | GLIBC_2.2.5 | documented | [glibc catalog](./overview.md) | —semaphore; semaphore |
| GLIBC-sem_trywait | sem_trywait | — | GLIBC_2.2.5 | documented | [glibc catalog](./overview.md) | —semaphore; semaphore |
| GLIBC-sem_unlink | sem_unlink | `semaphore.h` | GLIBC_2.2.5 | documented | [glibc catalog](./overview.md) | —semaphore; semaphore |
| GLIBC-sem_wait | sem_wait | `semaphore.h` | GLIBC_2.2.5 | documented | [glibc catalog](./overview.md) | —semaphore; semaphore |
| GLIBC-thrd_create | thrd_create | — | GLIBC_2.28 | documented | [glibc catalog](./overview.md) | —C11; C11 |
| GLIBC-thrd_current | thrd_current | — | — | documented | [glibc catalog](./overview.md) | —C11; C11 |
| GLIBC-thrd_detach | thrd_detach | — | GLIBC_2.28 | documented | [glibc catalog](./overview.md) | —C11; C11 |
| GLIBC-thrd_equal | thrd_equal | — | — | documented | [glibc catalog](./overview.md) | —C11; C11 |
| GLIBC-thrd_exit | thrd_exit | — | GLIBC_2.28 | documented | [glibc catalog](./overview.md) | —C11; C11 |
| GLIBC-thrd_join | thrd_join | — | GLIBC_2.28 | documented | [glibc catalog](./overview.md) | —C11; C11 |
| GLIBC-thrd_sleep | thrd_sleep | — | — | documented | [glibc catalog](./overview.md) | —C11; C11 |
| GLIBC-thrd_yield | thrd_yield | — | — | documented | [glibc catalog](./overview.md) | —C11; C11 |
| GLIBC-tss_create | tss_create | — | GLIBC_2.28 | documented | [glibc catalog](./overview.md) | —C11; C11 |
| GLIBC-tss_delete | tss_delete | — | GLIBC_2.28 | documented | [glibc catalog](./overview.md) | —C11; C11 |
| GLIBC-tss_get | tss_get | — | GLIBC_2.28 | documented | [glibc catalog](./overview.md) | —C11; C11 |
| GLIBC-tss_set | tss_set | — | GLIBC_2.28 | documented | [glibc catalog](./overview.md) | —C11; C11 |

### Users and Groups

| ID | Function | Header | Exported | Status | Chapter | Notes |
|---|---|---|---|---|---|---|
| GLIBC-cuserid | cuserid | — | — | documented | [glibc catalog](./overview.md) | —persona; persona |
| GLIBC-endgrent | endgrent | — | — | documented | [glibc catalog](./overview.md) | —grent; grent |
| GLIBC-endnetgrent | endnetgrent | — | — | documented | [glibc catalog](./overview.md) | —netgroup; netgroup |
| GLIBC-endpwent | endpwent | — | — | documented | [glibc catalog](./overview.md) | —pwent; pwent |
| GLIBC-endutent | endutent | — | — | documented | [glibc catalog](./overview.md) | —utmp; utmp |
| GLIBC-endutxent | endutxent | — | — | documented | [glibc catalog](./overview.md) | —utmpx; utmpx |
| GLIBC-fgetgrent | fgetgrent | `stdio.h` | — | documented | [glibc catalog](./overview.md) | —group-DB; group-DB |
| GLIBC-fgetgrent_r | fgetgrent_r | — | — | documented | [glibc catalog](./overview.md) | —group-DB; group-DB |
| GLIBC-fgetpwent | fgetpwent | `stdio.h` | — | documented | [glibc catalog](./overview.md) | —passwd-DB; passwd-DB |
| GLIBC-fgetpwent_r | fgetpwent_r | — | — | documented | [glibc catalog](./overview.md) | —passwd-DB; passwd-DB |
| GLIBC-getegid | getegid | — | — | documented | [glibc catalog](./overview.md) | —persona; persona |
| GLIBC-geteuid | geteuid | — | — | documented | [glibc catalog](./overview.md) | —persona; persona |
| GLIBC-getgid | getgid | — | — | documented | [glibc catalog](./overview.md) | —persona; persona |
| GLIBC-getgrent | getgrent | `sys/types.h` | — | documented | [glibc catalog](./overview.md) | —grent; grent |
| GLIBC-getgrent_r | getgrent_r | `grp.h` | — | documented | [glibc catalog](./overview.md) | —grent; grent |
| GLIBC-getgrgid | getgrgid | — | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-getgrgid_r | getgrgid_r | — | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-getgrnam | getgrnam | `sys/types.h` | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-getgrnam_r | getgrnam_r | — | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-getgrouplist | getgrouplist | `grp.h` | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-getgroups | getgroups | — | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-getlogin | getlogin | `unistd.h` | — | documented | [glibc catalog](./overview.md) | —persona; persona |
| GLIBC-getnetgrent | getnetgrent | — | — | documented | [glibc catalog](./overview.md) | —netgroup; netgroup |
| GLIBC-getnetgrent_r | getnetgrent_r | — | — | documented | [glibc catalog](./overview.md) | —netgroup; netgroup |
| GLIBC-getpwent | getpwent | `sys/types.h` | — | documented | [glibc catalog](./overview.md) | —pwent; pwent |
| GLIBC-getpwent_r | getpwent_r | `pwd.h` | — | documented | [glibc catalog](./overview.md) | —pwent; pwent |
| GLIBC-getpwnam | getpwnam | `sys/types.h` | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-getpwnam_r | getpwnam_r | — | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-getpwuid | getpwuid | — | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-getpwuid_r | getpwuid_r | — | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-getuid | getuid | — | — | documented | [glibc catalog](./overview.md) | —persona; persona |
| GLIBC-getutent | getutent | `utmp.h` | — | documented | [glibc catalog](./overview.md) | —utmp; utmp |
| GLIBC-getutent_r | getutent_r | — | — | documented | [glibc catalog](./overview.md) | —utmp; utmp |
| GLIBC-getutid | getutid | — | — | documented | [glibc catalog](./overview.md) | —utmp; utmp |
| GLIBC-getutid_r | getutid_r | — | — | documented | [glibc catalog](./overview.md) | —utmp; utmp |
| GLIBC-getutline | getutline | — | — | documented | [glibc catalog](./overview.md) | —utmp; utmp |
| GLIBC-getutline_r | getutline_r | — | — | documented | [glibc catalog](./overview.md) | —utmp; utmp |
| GLIBC-getutmp | getutmp | `utmpx.h` | — | documented | [glibc catalog](./overview.md) | —utmp/utmpx; utmp/utmpx |
| GLIBC-getutmpx | getutmpx | — | — | documented | [glibc catalog](./overview.md) | —utmp/utmpx; utmp/utmpx |
| GLIBC-getutxent | getutxent | — | — | documented | [glibc catalog](./overview.md) | —utmpx; utmpx |
| GLIBC-getutxid | getutxid | — | — | documented | [glibc catalog](./overview.md) | —utmpx; utmpx |
| GLIBC-getutxline | getutxline | — | — | documented | [glibc catalog](./overview.md) | —utmpx; utmpx |
| GLIBC-initgroups | initgroups | `sys/types.h` | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-innetgr | innetgr | — | — | documented | [glibc catalog](./overview.md) | —netgroup; netgroup |
| GLIBC-login | login | `utmp.h` | GLIBC_2.2.5 | documented | [glibc catalog](./overview.md) | —utmp/wtmp; utmp/wtmp |
| GLIBC-login_tty | login_tty | — | GLIBC_2.2.5 | documented | [glibc catalog](./overview.md) | —utmp/wtmp; utmp/wtmp |
| GLIBC-logout | logout | — | GLIBC_2.2.5 | documented | [glibc catalog](./overview.md) | —utmp/wtmp; utmp/wtmp |
| GLIBC-logwtmp | logwtmp | — | GLIBC_2.2.5 | documented | [glibc catalog](./overview.md) | —utmp/wtmp; utmp/wtmp |
| GLIBC-putpwent | putpwent | `stdio.h` | — | documented | [glibc catalog](./overview.md) | —passwd-DB; passwd-DB |
| GLIBC-pututline | pututline | — | — | documented | [glibc catalog](./overview.md) | —utmp; utmp |
| GLIBC-pututxline | pututxline | — | — | documented | [glibc catalog](./overview.md) | —utmpx; utmpx |
| GLIBC-setegid | setegid | — | — | documented | [glibc catalog](./overview.md) | —setuid-family; setuid-family |
| GLIBC-seteuid | seteuid | — | — | documented | [glibc catalog](./overview.md) | —setuid-family; setuid-family |
| GLIBC-setgid | setgid | — | — | documented | [glibc catalog](./overview.md) | —setuid-family; setuid-family |
| GLIBC-setgrent | setgrent | — | — | documented | [glibc catalog](./overview.md) | —grent; grent |
| GLIBC-setgroups | setgroups | — | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-setnetgrent | setnetgrent | `netdb.h` | — | documented | [glibc catalog](./overview.md) | —netgroup; netgroup |
| GLIBC-setpwent | setpwent | — | — | documented | [glibc catalog](./overview.md) | —pwent; pwent |
| GLIBC-setregid | setregid | — | — | documented | [glibc catalog](./overview.md) | —setuid-family; setuid-family |
| GLIBC-setreuid | setreuid | — | — | documented | [glibc catalog](./overview.md) | —setuid-family; setuid-family |
| GLIBC-setuid | setuid | — | — | documented | [glibc catalog](./overview.md) | —setuid-family; setuid-family |
| GLIBC-setutent | setutent | — | — | documented | [glibc catalog](./overview.md) | —utmp; utmp |
| GLIBC-setutxent | setutxent | — | — | documented | [glibc catalog](./overview.md) | —utmpx; utmpx |
| GLIBC-updwtmp | updwtmp | `utmp.h` | — | documented | [glibc catalog](./overview.md) | —utmp/wtmp; utmp/wtmp |
| GLIBC-utmpname | utmpname | — | — | documented | [glibc catalog](./overview.md) | —utmp; utmp |
| GLIBC-utmpxname | utmpxname | — | — | documented | [glibc catalog](./overview.md) | —utmpx; utmpx |

### Virtual Memory Allocation And Paging

| ID | Function | Header | Exported | Status | Chapter | Notes |
|---|---|---|---|---|---|---|
| GLIBC-aligned_alloc | aligned_alloc | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-alloca | alloca | `alloca.h` | — | documented | [glibc catalog](./overview.md) | —allocation; allocation |
| GLIBC-brk | brk | — | — | documented | [glibc catalog](./overview.md) | —allocation; allocation |
| GLIBC-calloc | calloc | — | — | documented | [glibc catalog](./overview.md) | —full; full |
| GLIBC-free | free | — | — | documented | [glibc catalog](./overview.md) | —full; full |
| GLIBC-free_aligned_sized | free_aligned_sized | — | — | source-limited | [glibc catalog](./overview.md) | —allocation; allocation |
| GLIBC-free_sized | free_sized | — | — | source-limited | [glibc catalog](./overview.md) | —allocation; allocation |
| GLIBC-mallinfo2 | mallinfo2 | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-malloc | malloc | `stdlib.h` | — | documented | [glibc catalog](./overview.md) | —full; full |
| GLIBC-mallopt | mallopt | `malloc.h` | — | documented | [glibc catalog](./overview.md) | —full; full |
| GLIBC-mcheck | mcheck | `mcheck.h` | — | documented | [glibc catalog](./overview.md) | —allocation; allocation |
| GLIBC-memalign | memalign | — | — | documented | [glibc catalog](./overview.md) | —allocation; allocation |
| GLIBC-memalignment | memalignment | — | — | source-limited | [glibc catalog](./overview.md) | —allocation; allocation |
| GLIBC-mlock | mlock | — | — | documented | [glibc catalog](./overview.md) | —allocation; allocation |
| GLIBC-mlock2 | mlock2 | — | — | documented | [glibc catalog](./overview.md) | —allocation; allocation |
| GLIBC-mlockall | mlockall | — | — | documented | [glibc catalog](./overview.md) | —allocation; allocation |
| GLIBC-mprobe | mprobe | — | — | documented | [glibc catalog](./overview.md) | —allocation; allocation |
| GLIBC-mprotect | mprotect | — | — | documented | [glibc catalog](./overview.md) | —allocation; allocation |
| GLIBC-mseal | mseal | — | — | source-limited | [glibc catalog](./overview.md) | —allocation; allocation |
| GLIBC-mtrace | mtrace | `mcheck.h` | — | documented | [glibc catalog](./overview.md) | —allocation; allocation |
| GLIBC-munlock | munlock | — | — | documented | [glibc catalog](./overview.md) | —allocation; allocation |
| GLIBC-munlockall | munlockall | — | — | documented | [glibc catalog](./overview.md) | —allocation; allocation |
| GLIBC-muntrace | muntrace | — | — | documented | [glibc catalog](./overview.md) | —allocation; allocation |
| GLIBC-obstack_1grow | obstack_1grow | — | — | documented | [glibc catalog](./overview.md) | —obstack; obstack |
| GLIBC-obstack_1grow_fast | obstack_1grow_fast | — | — | documented | [glibc catalog](./overview.md) | —obstack; obstack |
| GLIBC-obstack_alloc | obstack_alloc | — | — | documented | [glibc catalog](./overview.md) | —obstack; obstack |
| GLIBC-obstack_base | obstack_base | — | — | documented | [glibc catalog](./overview.md) | —obstack; obstack |
| GLIBC-obstack_blank | obstack_blank | — | — | documented | [glibc catalog](./overview.md) | —obstack; obstack |
| GLIBC-obstack_blank_fast | obstack_blank_fast | — | — | documented | [glibc catalog](./overview.md) | —obstack; obstack |
| GLIBC-obstack_copy | obstack_copy | — | — | documented | [glibc catalog](./overview.md) | —obstack; obstack |
| GLIBC-obstack_copy0 | obstack_copy0 | — | — | documented | [glibc catalog](./overview.md) | —obstack; obstack |
| GLIBC-obstack_finish | obstack_finish | — | — | documented | [glibc catalog](./overview.md) | —obstack; obstack |
| GLIBC-obstack_free | obstack_free | — | — | documented | [glibc catalog](./overview.md) | —obstack; obstack |
| GLIBC-obstack_grow | obstack_grow | — | — | documented | [glibc catalog](./overview.md) | —obstack; obstack |
| GLIBC-obstack_grow0 | obstack_grow0 | — | — | documented | [glibc catalog](./overview.md) | —obstack; obstack |
| GLIBC-obstack_init | obstack_init | — | — | documented | [glibc catalog](./overview.md) | —obstack; obstack |
| GLIBC-obstack_int_grow | obstack_int_grow | — | — | documented | [glibc catalog](./overview.md) | —obstack; obstack |
| GLIBC-obstack_int_grow_fast | obstack_int_grow_fast | — | — | documented | [glibc catalog](./overview.md) | —obstack; obstack |
| GLIBC-obstack_next_free | obstack_next_free | — | — | documented | [glibc catalog](./overview.md) | —obstack; obstack |
| GLIBC-obstack_object_size | obstack_object_size | — | — | documented | [glibc catalog](./overview.md) | —obstack; obstack |
| GLIBC-obstack_ptr_grow | obstack_ptr_grow | — | — | documented | [glibc catalog](./overview.md) | —obstack; obstack |
| GLIBC-obstack_ptr_grow_fast | obstack_ptr_grow_fast | — | — | documented | [glibc catalog](./overview.md) | —obstack; obstack |
| GLIBC-obstack_room | obstack_room | — | — | documented | [glibc catalog](./overview.md) | —obstack; obstack |
| GLIBC-pkey_alloc | pkey_alloc | — | — | documented | [glibc catalog](./overview.md) | —allocation; allocation |
| GLIBC-pkey_free | pkey_free | — | — | documented | [glibc catalog](./overview.md) | —allocation; allocation |
| GLIBC-pkey_get | pkey_get | — | — | documented | [glibc catalog](./overview.md) | —allocation; allocation |
| GLIBC-pkey_mprotect | pkey_mprotect | — | — | documented | [glibc catalog](./overview.md) | —allocation; allocation |
| GLIBC-pkey_set | pkey_set | — | — | documented | [glibc catalog](./overview.md) | —allocation; allocation |
| GLIBC-posix_memalign | posix_memalign | `stdlib.h` | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-realloc | realloc | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-reallocarray | reallocarray | — | — | documented | [glibc catalog](./overview.md) | —grouped; grouped |
| GLIBC-sbrk | sbrk | — | — | documented | [glibc catalog](./overview.md) | —allocation; allocation |
| GLIBC-valloc | valloc | — | — | documented | [glibc catalog](./overview.md) | —allocation; allocation |

### argp.texi

| ID | Function | Header | Exported | Status | Chapter | Notes |
|---|---|---|---|---|---|---|
| GLIBC-argp_error | argp_error | — | — | documented | [glibc catalog](./overview.md) | —argp; argp |
| GLIBC-argp_failure | argp_failure | — | — | documented | [glibc catalog](./overview.md) | —argp; argp |
| GLIBC-argp_help | argp_help | — | — | documented | [glibc catalog](./overview.md) | —argp; argp |
| GLIBC-argp_parse | argp_parse | — | — | documented | [glibc catalog](./overview.md) | —argp; argp |
| GLIBC-argp_state_help | argp_state_help | — | — | documented | [glibc catalog](./overview.md) | —argp; argp |
| GLIBC-argp_usage | argp_usage | — | — | documented | [glibc catalog](./overview.md) | —argp; argp |

### getopt.texi

| ID | Function | Header | Exported | Status | Chapter | Notes |
|---|---|---|---|---|---|---|
| GLIBC-getopt | getopt | `unistd.h` | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-getopt_long | getopt_long | — | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |
| GLIBC-getopt_long_only | getopt_long_only | — | — | documented | [glibc catalog](./overview.md) | —Grouped; Grouped |

### platform.texi

| ID | Function | Header | Exported | Status | Chapter | Notes |
|---|---|---|---|---|---|---|
| GLIBC-__ppc_get_timebase | __ppc_get_timebase | `sys/platform/ppc.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-__ppc_get_timebase_freq | __ppc_get_timebase_freq | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-__ppc_mdoio | __ppc_mdoio | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-__ppc_mdoom | __ppc_mdoom | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-__ppc_set_ppr_low | __ppc_set_ppr_low | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-__ppc_set_ppr_med | __ppc_set_ppr_med | `sys/platform/ppc.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-__ppc_set_ppr_med_high | __ppc_set_ppr_med_high | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-__ppc_set_ppr_med_low | __ppc_set_ppr_med_low | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-__ppc_set_ppr_very_low | __ppc_set_ppr_very_low | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-__ppc_yield | __ppc_yield | `sys/platform/ppc.h` | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-__riscv_flush_icache | __riscv_flush_icache | — | — | not-started | [glibc catalog](./overview.md) | — |
| GLIBC-__x86_get_cpuid_feature_leaf | __x86_get_cpuid_feature_leaf | — | — | not-started | [glibc catalog](./overview.md) | — |

Documented functions: 1881. Exported (non-private, non-`__`) symbols: 3470. Rows in triage queue: 1953.

## Exported but undocumented (triage queue)

Names that appear in the dynamic symbol table but have no `@deftypefun` in
the manual. Typical causes: manual documents a family without a dedicated
prototype (rare), compatibility aliases, or versioned alternate names. They
are listed for completeness; documenting them individually is out of scope
unless they are public documented APIs under another spelling.

| ID | Name | Exported from | Newest symbol version | Status |
|---|---|---|---|---|
| GLIBC-_authenticate | _authenticate | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-_dl_mcount_wrapper | _dl_mcount_wrapper | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-_dl_mcount_wrapper_check | _dl_mcount_wrapper_check | libc.so.6 | — | not-started |
| GLIBC-_gethtbyaddr | _gethtbyaddr | libresolv.so.2 | GLIBC_2.2.5 | not-started |
| GLIBC-_gethtbyname | _gethtbyname | libresolv.so.2 | GLIBC_2.2.5 | not-started |
| GLIBC-_gethtbyname2 | _gethtbyname2 | libresolv.so.2 | GLIBC_2.2.5 | not-started |
| GLIBC-_gethtent | _gethtent | libresolv.so.2 | GLIBC_2.2.5 | not-started |
| GLIBC-_getlong | _getlong | libresolv.so.2 | — | not-started |
| GLIBC-_getshort | _getshort | libresolv.so.2 | — | not-started |
| GLIBC-_IO_2_1_stderr_ | _IO_2_1_stderr_ | libc.so.6 | — | not-started |
| GLIBC-_IO_2_1_stdin_ | _IO_2_1_stdin_ | libc.so.6 | — | not-started |
| GLIBC-_IO_2_1_stdout_ | _IO_2_1_stdout_ | libc.so.6 | — | not-started |
| GLIBC-_IO_adjust_column | _IO_adjust_column | libc.so.6 | — | not-started |
| GLIBC-_IO_adjust_wcolumn | _IO_adjust_wcolumn | libc.so.6 | — | not-started |
| GLIBC-_IO_default_doallocate | _IO_default_doallocate | libc.so.6 | — | not-started |
| GLIBC-_IO_default_finish | _IO_default_finish | libc.so.6 | — | not-started |
| GLIBC-_IO_default_pbackfail | _IO_default_pbackfail | libc.so.6 | — | not-started |
| GLIBC-_IO_default_uflow | _IO_default_uflow | libc.so.6 | — | not-started |
| GLIBC-_IO_default_xsgetn | _IO_default_xsgetn | libc.so.6 | — | not-started |
| GLIBC-_IO_default_xsputn | _IO_default_xsputn | libc.so.6 | — | not-started |
| GLIBC-_IO_do_write | _IO_do_write | libc.so.6 | — | not-started |
| GLIBC-_IO_doallocbuf | _IO_doallocbuf | libc.so.6 | — | not-started |
| GLIBC-_IO_enable_locks | _IO_enable_locks | libc.so.6 | — | not-started |
| GLIBC-_IO_fclose | _IO_fclose | libc.so.6 | — | not-started |
| GLIBC-_IO_fdopen | _IO_fdopen | libc.so.6 | — | not-started |
| GLIBC-_IO_feof | _IO_feof | libc.so.6 | — | not-started |
| GLIBC-_IO_ferror | _IO_ferror | libc.so.6 | — | not-started |
| GLIBC-_IO_fflush | _IO_fflush | libc.so.6 | — | not-started |
| GLIBC-_IO_fgetpos | _IO_fgetpos | libc.so.6 | — | not-started |
| GLIBC-_IO_fgetpos64 | _IO_fgetpos64 | libc.so.6 | — | not-started |
| GLIBC-_IO_fgets | _IO_fgets | libc.so.6 | — | not-started |
| GLIBC-_IO_file_attach | _IO_file_attach | libc.so.6 | — | not-started |
| GLIBC-_IO_file_close | _IO_file_close | libc.so.6 | — | not-started |
| GLIBC-_IO_file_close_it | _IO_file_close_it | libc.so.6 | — | not-started |
| GLIBC-_IO_file_doallocate | _IO_file_doallocate | libc.so.6 | — | not-started |
| GLIBC-_IO_file_finish | _IO_file_finish | libc.so.6 | — | not-started |
| GLIBC-_IO_file_fopen | _IO_file_fopen | libc.so.6 | — | not-started |
| GLIBC-_IO_file_init | _IO_file_init | libc.so.6 | — | not-started |
| GLIBC-_IO_file_jumps | _IO_file_jumps | libc.so.6 | — | not-started |
| GLIBC-_IO_file_open | _IO_file_open | libc.so.6 | — | not-started |
| GLIBC-_IO_file_overflow | _IO_file_overflow | libc.so.6 | — | not-started |
| GLIBC-_IO_file_read | _IO_file_read | libc.so.6 | — | not-started |
| GLIBC-_IO_file_seek | _IO_file_seek | libc.so.6 | — | not-started |
| GLIBC-_IO_file_seekoff | _IO_file_seekoff | libc.so.6 | — | not-started |
| GLIBC-_IO_file_setbuf | _IO_file_setbuf | libc.so.6 | — | not-started |
| GLIBC-_IO_file_stat | _IO_file_stat | libc.so.6 | — | not-started |
| GLIBC-_IO_file_sync | _IO_file_sync | libc.so.6 | — | not-started |
| GLIBC-_IO_file_underflow | _IO_file_underflow | libc.so.6 | — | not-started |
| GLIBC-_IO_file_write | _IO_file_write | libc.so.6 | — | not-started |
| GLIBC-_IO_file_xsputn | _IO_file_xsputn | libc.so.6 | — | not-started |
| GLIBC-_IO_flockfile | _IO_flockfile | libc.so.6 | — | not-started |
| GLIBC-_IO_flush_all | _IO_flush_all | libc.so.6 | — | not-started |
| GLIBC-_IO_flush_all_linebuffered | _IO_flush_all_linebuffered | libc.so.6 | — | not-started |
| GLIBC-_IO_fopen | _IO_fopen | libc.so.6 | — | not-started |
| GLIBC-_IO_fprintf | _IO_fprintf | libc.so.6 | — | not-started |
| GLIBC-_IO_fputs | _IO_fputs | libc.so.6 | — | not-started |
| GLIBC-_IO_fread | _IO_fread | libc.so.6 | — | not-started |
| GLIBC-_IO_free_backup_area | _IO_free_backup_area | libc.so.6 | — | not-started |
| GLIBC-_IO_free_wbackup_area | _IO_free_wbackup_area | libc.so.6 | — | not-started |
| GLIBC-_IO_fsetpos | _IO_fsetpos | libc.so.6 | — | not-started |
| GLIBC-_IO_fsetpos64 | _IO_fsetpos64 | libc.so.6 | — | not-started |
| GLIBC-_IO_ftell | _IO_ftell | libc.so.6 | — | not-started |
| GLIBC-_IO_ftrylockfile | _IO_ftrylockfile | libc.so.6 | — | not-started |
| GLIBC-_IO_funlockfile | _IO_funlockfile | libc.so.6 | — | not-started |
| GLIBC-_IO_fwrite | _IO_fwrite | libc.so.6 | — | not-started |
| GLIBC-_IO_getc | _IO_getc | libc.so.6 | — | not-started |
| GLIBC-_IO_getline | _IO_getline | libc.so.6 | — | not-started |
| GLIBC-_IO_getline_info | _IO_getline_info | libc.so.6 | — | not-started |
| GLIBC-_IO_gets | _IO_gets | libc.so.6 | — | not-started |
| GLIBC-_IO_init | _IO_init | libc.so.6 | — | not-started |
| GLIBC-_IO_init_marker | _IO_init_marker | libc.so.6 | — | not-started |
| GLIBC-_IO_init_wmarker | _IO_init_wmarker | libc.so.6 | — | not-started |
| GLIBC-_IO_iter_begin | _IO_iter_begin | libc.so.6 | — | not-started |
| GLIBC-_IO_iter_end | _IO_iter_end | libc.so.6 | — | not-started |
| GLIBC-_IO_iter_file | _IO_iter_file | libc.so.6 | — | not-started |
| GLIBC-_IO_iter_next | _IO_iter_next | libc.so.6 | — | not-started |
| GLIBC-_IO_least_wmarker | _IO_least_wmarker | libc.so.6 | — | not-started |
| GLIBC-_IO_link_in | _IO_link_in | libc.so.6 | — | not-started |
| GLIBC-_IO_list_all | _IO_list_all | libc.so.6 | — | not-started |
| GLIBC-_IO_list_lock | _IO_list_lock | libc.so.6 | — | not-started |
| GLIBC-_IO_list_resetlock | _IO_list_resetlock | libc.so.6 | — | not-started |
| GLIBC-_IO_list_unlock | _IO_list_unlock | libc.so.6 | — | not-started |
| GLIBC-_IO_marker_delta | _IO_marker_delta | libc.so.6 | — | not-started |
| GLIBC-_IO_marker_difference | _IO_marker_difference | libc.so.6 | — | not-started |
| GLIBC-_IO_padn | _IO_padn | libc.so.6 | — | not-started |
| GLIBC-_IO_peekc_locked | _IO_peekc_locked | libc.so.6 | — | not-started |
| GLIBC-_IO_popen | _IO_popen | libc.so.6 | — | not-started |
| GLIBC-_IO_printf | _IO_printf | libc.so.6 | — | not-started |
| GLIBC-_IO_proc_close | _IO_proc_close | libc.so.6 | — | not-started |
| GLIBC-_IO_proc_open | _IO_proc_open | libc.so.6 | — | not-started |
| GLIBC-_IO_putc | _IO_putc | libc.so.6 | — | not-started |
| GLIBC-_IO_puts | _IO_puts | libc.so.6 | — | not-started |
| GLIBC-_IO_remove_marker | _IO_remove_marker | libc.so.6 | — | not-started |
| GLIBC-_IO_seekmark | _IO_seekmark | libc.so.6 | — | not-started |
| GLIBC-_IO_seekoff | _IO_seekoff | libc.so.6 | — | not-started |
| GLIBC-_IO_seekpos | _IO_seekpos | libc.so.6 | — | not-started |
| GLIBC-_IO_seekwmark | _IO_seekwmark | libc.so.6 | — | not-started |
| GLIBC-_IO_setb | _IO_setb | libc.so.6 | — | not-started |
| GLIBC-_IO_setbuffer | _IO_setbuffer | libc.so.6 | — | not-started |
| GLIBC-_IO_setvbuf | _IO_setvbuf | libc.so.6 | — | not-started |
| GLIBC-_IO_sgetn | _IO_sgetn | libc.so.6 | — | not-started |
| GLIBC-_IO_sprintf | _IO_sprintf | libc.so.6 | — | not-started |
| GLIBC-_IO_sputbackc | _IO_sputbackc | libc.so.6 | — | not-started |
| GLIBC-_IO_sputbackwc | _IO_sputbackwc | libc.so.6 | — | not-started |
| GLIBC-_IO_sscanf | _IO_sscanf | libc.so.6 | — | not-started |
| GLIBC-_IO_str_init_readonly | _IO_str_init_readonly | libc.so.6 | — | not-started |
| GLIBC-_IO_str_init_static | _IO_str_init_static | libc.so.6 | — | not-started |
| GLIBC-_IO_str_overflow | _IO_str_overflow | libc.so.6 | — | not-started |
| GLIBC-_IO_str_pbackfail | _IO_str_pbackfail | libc.so.6 | — | not-started |
| GLIBC-_IO_str_seekoff | _IO_str_seekoff | libc.so.6 | — | not-started |
| GLIBC-_IO_str_underflow | _IO_str_underflow | libc.so.6 | — | not-started |
| GLIBC-_IO_sungetc | _IO_sungetc | libc.so.6 | — | not-started |
| GLIBC-_IO_sungetwc | _IO_sungetwc | libc.so.6 | — | not-started |
| GLIBC-_IO_switch_to_get_mode | _IO_switch_to_get_mode | libc.so.6 | — | not-started |
| GLIBC-_IO_switch_to_main_wget_area | _IO_switch_to_main_wget_area | libc.so.6 | — | not-started |
| GLIBC-_IO_switch_to_wbackup_area | _IO_switch_to_wbackup_area | libc.so.6 | — | not-started |
| GLIBC-_IO_switch_to_wget_mode | _IO_switch_to_wget_mode | libc.so.6 | — | not-started |
| GLIBC-_IO_un_link | _IO_un_link | libc.so.6 | — | not-started |
| GLIBC-_IO_ungetc | _IO_ungetc | libc.so.6 | — | not-started |
| GLIBC-_IO_unsave_markers | _IO_unsave_markers | libc.so.6 | — | not-started |
| GLIBC-_IO_unsave_wmarkers | _IO_unsave_wmarkers | libc.so.6 | — | not-started |
| GLIBC-_IO_vfprintf | _IO_vfprintf | libc.so.6 | — | not-started |
| GLIBC-_IO_vfscanf | _IO_vfscanf | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-_IO_vsprintf | _IO_vsprintf | libc.so.6 | — | not-started |
| GLIBC-_IO_wdefault_doallocate | _IO_wdefault_doallocate | libc.so.6 | — | not-started |
| GLIBC-_IO_wdefault_finish | _IO_wdefault_finish | libc.so.6 | — | not-started |
| GLIBC-_IO_wdefault_pbackfail | _IO_wdefault_pbackfail | libc.so.6 | — | not-started |
| GLIBC-_IO_wdefault_uflow | _IO_wdefault_uflow | libc.so.6 | — | not-started |
| GLIBC-_IO_wdefault_xsgetn | _IO_wdefault_xsgetn | libc.so.6 | — | not-started |
| GLIBC-_IO_wdefault_xsputn | _IO_wdefault_xsputn | libc.so.6 | — | not-started |
| GLIBC-_IO_wdo_write | _IO_wdo_write | libc.so.6 | — | not-started |
| GLIBC-_IO_wdoallocbuf | _IO_wdoallocbuf | libc.so.6 | — | not-started |
| GLIBC-_IO_wfile_jumps | _IO_wfile_jumps | libc.so.6 | — | not-started |
| GLIBC-_IO_wfile_overflow | _IO_wfile_overflow | libc.so.6 | — | not-started |
| GLIBC-_IO_wfile_seekoff | _IO_wfile_seekoff | libc.so.6 | — | not-started |
| GLIBC-_IO_wfile_sync | _IO_wfile_sync | libc.so.6 | — | not-started |
| GLIBC-_IO_wfile_underflow | _IO_wfile_underflow | libc.so.6 | — | not-started |
| GLIBC-_IO_wfile_xsputn | _IO_wfile_xsputn | libc.so.6 | — | not-started |
| GLIBC-_IO_wmarker_delta | _IO_wmarker_delta | libc.so.6 | — | not-started |
| GLIBC-_IO_wsetb | _IO_wsetb | libc.so.6 | — | not-started |
| GLIBC-_itoa_lower_digits | _itoa_lower_digits | libc.so.6 | — | not-started |
| GLIBC-_LIB_VERSION | _LIB_VERSION | libm.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-_libc_intl_domainname | _libc_intl_domainname | libc.so.6 | — | not-started |
| GLIBC-_longjmp | _longjmp | libc.so.6 | — | not-started |
| GLIBC-_mcleanup | _mcleanup | libc.so.6 | — | not-started |
| GLIBC-_mcount | _mcount | libc.so.6 | — | not-started |
| GLIBC-_nl_default_dirname | _nl_default_dirname | libc.so.6 | — | not-started |
| GLIBC-_nl_domain_bindings | _nl_domain_bindings | libc.so.6 | — | not-started |
| GLIBC-_nl_msg_cat_cntr | _nl_msg_cat_cntr | libc.so.6 | — | not-started |
| GLIBC-_nss_dns_getcanonname_r | _nss_dns_getcanonname_r | libc.so.6 | — | not-started |
| GLIBC-_nss_dns_gethostbyaddr2_r | _nss_dns_gethostbyaddr2_r | libc.so.6 | — | not-started |
| GLIBC-_nss_dns_gethostbyaddr_r | _nss_dns_gethostbyaddr_r | libc.so.6 | — | not-started |
| GLIBC-_nss_dns_gethostbyname2_r | _nss_dns_gethostbyname2_r | libc.so.6 | — | not-started |
| GLIBC-_nss_dns_gethostbyname3_r | _nss_dns_gethostbyname3_r | libc.so.6 | — | not-started |
| GLIBC-_nss_dns_gethostbyname4_r | _nss_dns_gethostbyname4_r | libc.so.6 | — | not-started |
| GLIBC-_nss_dns_gethostbyname_r | _nss_dns_gethostbyname_r | libc.so.6 | — | not-started |
| GLIBC-_nss_dns_getnetbyaddr_r | _nss_dns_getnetbyaddr_r | libc.so.6 | — | not-started |
| GLIBC-_nss_dns_getnetbyname_r | _nss_dns_getnetbyname_r | libc.so.6 | — | not-started |
| GLIBC-_nss_files_endaliasent | _nss_files_endaliasent | libc.so.6 | — | not-started |
| GLIBC-_nss_files_endetherent | _nss_files_endetherent | libc.so.6 | — | not-started |
| GLIBC-_nss_files_endgrent | _nss_files_endgrent | libc.so.6 | — | not-started |
| GLIBC-_nss_files_endhostent | _nss_files_endhostent | libc.so.6 | — | not-started |
| GLIBC-_nss_files_endnetent | _nss_files_endnetent | libc.so.6 | — | not-started |
| GLIBC-_nss_files_endnetgrent | _nss_files_endnetgrent | libc.so.6 | — | not-started |
| GLIBC-_nss_files_endprotoent | _nss_files_endprotoent | libc.so.6 | — | not-started |
| GLIBC-_nss_files_endpwent | _nss_files_endpwent | libc.so.6 | — | not-started |
| GLIBC-_nss_files_endrpcent | _nss_files_endrpcent | libc.so.6 | — | not-started |
| GLIBC-_nss_files_endservent | _nss_files_endservent | libc.so.6 | — | not-started |
| GLIBC-_nss_files_endsgent | _nss_files_endsgent | libc.so.6 | — | not-started |
| GLIBC-_nss_files_endspent | _nss_files_endspent | libc.so.6 | — | not-started |
| GLIBC-_nss_files_getaliasbyname_r | _nss_files_getaliasbyname_r | libc.so.6 | — | not-started |
| GLIBC-_nss_files_getaliasent_r | _nss_files_getaliasent_r | libc.so.6 | — | not-started |
| GLIBC-_nss_files_getetherent_r | _nss_files_getetherent_r | libc.so.6 | — | not-started |
| GLIBC-_nss_files_getgrent_r | _nss_files_getgrent_r | libc.so.6 | — | not-started |
| GLIBC-_nss_files_getgrgid_r | _nss_files_getgrgid_r | libc.so.6 | — | not-started |
| GLIBC-_nss_files_getgrnam_r | _nss_files_getgrnam_r | libc.so.6 | — | not-started |
| GLIBC-_nss_files_gethostbyaddr_r | _nss_files_gethostbyaddr_r | libc.so.6 | — | not-started |
| GLIBC-_nss_files_gethostbyname2_r | _nss_files_gethostbyname2_r | libc.so.6 | — | not-started |
| GLIBC-_nss_files_gethostbyname3_r | _nss_files_gethostbyname3_r | libc.so.6 | — | not-started |
| GLIBC-_nss_files_gethostbyname4_r | _nss_files_gethostbyname4_r | libc.so.6 | — | not-started |
| GLIBC-_nss_files_gethostbyname_r | _nss_files_gethostbyname_r | libc.so.6 | — | not-started |
| GLIBC-_nss_files_gethostent_r | _nss_files_gethostent_r | libc.so.6 | — | not-started |
| GLIBC-_nss_files_gethostton_r | _nss_files_gethostton_r | libc.so.6 | — | not-started |
| GLIBC-_nss_files_getnetbyaddr_r | _nss_files_getnetbyaddr_r | libc.so.6 | — | not-started |
| GLIBC-_nss_files_getnetbyname_r | _nss_files_getnetbyname_r | libc.so.6 | — | not-started |
| GLIBC-_nss_files_getnetent_r | _nss_files_getnetent_r | libc.so.6 | — | not-started |
| GLIBC-_nss_files_getnetgrent_r | _nss_files_getnetgrent_r | libc.so.6 | — | not-started |
| GLIBC-_nss_files_getntohost_r | _nss_files_getntohost_r | libc.so.6 | — | not-started |
| GLIBC-_nss_files_getprotobyname_r | _nss_files_getprotobyname_r | libc.so.6 | — | not-started |
| GLIBC-_nss_files_getprotobynumber_r | _nss_files_getprotobynumber_r | libc.so.6 | — | not-started |
| GLIBC-_nss_files_getprotoent_r | _nss_files_getprotoent_r | libc.so.6 | — | not-started |
| GLIBC-_nss_files_getpwent_r | _nss_files_getpwent_r | libc.so.6 | — | not-started |
| GLIBC-_nss_files_getpwnam_r | _nss_files_getpwnam_r | libc.so.6 | — | not-started |
| GLIBC-_nss_files_getpwuid_r | _nss_files_getpwuid_r | libc.so.6 | — | not-started |
| GLIBC-_nss_files_getrpcbyname_r | _nss_files_getrpcbyname_r | libc.so.6 | — | not-started |
| GLIBC-_nss_files_getrpcbynumber_r | _nss_files_getrpcbynumber_r | libc.so.6 | — | not-started |
| GLIBC-_nss_files_getrpcent_r | _nss_files_getrpcent_r | libc.so.6 | — | not-started |
| GLIBC-_nss_files_getservbyname_r | _nss_files_getservbyname_r | libc.so.6 | — | not-started |
| GLIBC-_nss_files_getservbyport_r | _nss_files_getservbyport_r | libc.so.6 | — | not-started |
| GLIBC-_nss_files_getservent_r | _nss_files_getservent_r | libc.so.6 | — | not-started |
| GLIBC-_nss_files_getsgent_r | _nss_files_getsgent_r | libc.so.6 | — | not-started |
| GLIBC-_nss_files_getsgnam_r | _nss_files_getsgnam_r | libc.so.6 | — | not-started |
| GLIBC-_nss_files_getspent_r | _nss_files_getspent_r | libc.so.6 | — | not-started |
| GLIBC-_nss_files_getspnam_r | _nss_files_getspnam_r | libc.so.6 | — | not-started |
| GLIBC-_nss_files_init | _nss_files_init | libc.so.6 | — | not-started |
| GLIBC-_nss_files_initgroups_dyn | _nss_files_initgroups_dyn | libc.so.6 | — | not-started |
| GLIBC-_nss_files_parse_etherent | _nss_files_parse_etherent | libc.so.6 | — | not-started |
| GLIBC-_nss_files_parse_grent | _nss_files_parse_grent | libc.so.6 | — | not-started |
| GLIBC-_nss_files_parse_netent | _nss_files_parse_netent | libc.so.6 | — | not-started |
| GLIBC-_nss_files_parse_protoent | _nss_files_parse_protoent | libc.so.6 | — | not-started |
| GLIBC-_nss_files_parse_pwent | _nss_files_parse_pwent | libc.so.6 | — | not-started |
| GLIBC-_nss_files_parse_rpcent | _nss_files_parse_rpcent | libc.so.6 | — | not-started |
| GLIBC-_nss_files_parse_servent | _nss_files_parse_servent | libc.so.6 | — | not-started |
| GLIBC-_nss_files_parse_sgent | _nss_files_parse_sgent | libc.so.6 | — | not-started |
| GLIBC-_nss_files_parse_spent | _nss_files_parse_spent | libc.so.6 | — | not-started |
| GLIBC-_nss_files_setaliasent | _nss_files_setaliasent | libc.so.6 | — | not-started |
| GLIBC-_nss_files_setetherent | _nss_files_setetherent | libc.so.6 | — | not-started |
| GLIBC-_nss_files_setgrent | _nss_files_setgrent | libc.so.6 | — | not-started |
| GLIBC-_nss_files_sethostent | _nss_files_sethostent | libc.so.6 | — | not-started |
| GLIBC-_nss_files_setnetent | _nss_files_setnetent | libc.so.6 | — | not-started |
| GLIBC-_nss_files_setnetgrent | _nss_files_setnetgrent | libc.so.6 | — | not-started |
| GLIBC-_nss_files_setprotoent | _nss_files_setprotoent | libc.so.6 | — | not-started |
| GLIBC-_nss_files_setpwent | _nss_files_setpwent | libc.so.6 | — | not-started |
| GLIBC-_nss_files_setrpcent | _nss_files_setrpcent | libc.so.6 | — | not-started |
| GLIBC-_nss_files_setservent | _nss_files_setservent | libc.so.6 | — | not-started |
| GLIBC-_nss_files_setsgent | _nss_files_setsgent | libc.so.6 | — | not-started |
| GLIBC-_nss_files_setspent | _nss_files_setspent | libc.so.6 | — | not-started |
| GLIBC-_nss_netgroup_parseline | _nss_netgroup_parseline | libc.so.6 | — | not-started |
| GLIBC-_null_auth | _null_auth | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-_obstack | _obstack | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-_obstack_allocated_p | _obstack_allocated_p | libc.so.6 | — | not-started |
| GLIBC-_obstack_begin | _obstack_begin | libc.so.6 | — | not-started |
| GLIBC-_obstack_begin_1 | _obstack_begin_1 | libc.so.6 | — | not-started |
| GLIBC-_obstack_free | _obstack_free | libc.so.6 | — | not-started |
| GLIBC-_obstack_memory_used | _obstack_memory_used | libc.so.6 | — | not-started |
| GLIBC-_obstack_newchunk | _obstack_newchunk | libc.so.6 | — | not-started |
| GLIBC-_pthread_cleanup_pop | _pthread_cleanup_pop | libc.so.6 | GLIBC_2.2.5 | documented; triage |
| GLIBC-_pthread_cleanup_pop_restore | _pthread_cleanup_pop_restore | libc.so.6 | GLIBC_2.2.5 | documented; triage |
| GLIBC-_pthread_cleanup_push | _pthread_cleanup_push | libc.so.6 | GLIBC_2.2.5 | documented; triage |
| GLIBC-_pthread_cleanup_push_defer | _pthread_cleanup_push_defer | libc.so.6 | GLIBC_2.2.5 | documented; triage |
| GLIBC-_res | _res | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-_res_hconf | _res_hconf | libc.so.6 | — | not-started |
| GLIBC-_res_opcodes | _res_opcodes | libresolv.so.2 | GLIBC_2.2.5 | not-started |
| GLIBC-_rpc_dtablesize | _rpc_dtablesize | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-_seterr_reply | _seterr_reply | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-_sethtent | _sethtent | libresolv.so.2 | GLIBC_2.2.5 | not-started |
| GLIBC-_setjmp | _setjmp | libc.so.6 | — | documented; full |
| GLIBC-_sys_errlist | _sys_errlist | libc.so.6 | GLIBC_2.4 | not-started |
| GLIBC-_sys_nerr | _sys_nerr | libc.so.6 | GLIBC_2.4 | not-started |
| GLIBC-_sys_siglist | _sys_siglist | libc.so.6 | GLIBC_2.3.3 | not-started |
| GLIBC-_thread_db___nptl_last_event | _thread_db___nptl_last_event | libc.so.6 | — | not-started |
| GLIBC-_thread_db___nptl_nthreads | _thread_db___nptl_nthreads | libc.so.6 | — | not-started |
| GLIBC-_thread_db___nptl_rtld_global | _thread_db___nptl_rtld_global | libc.so.6 | — | not-started |
| GLIBC-_thread_db___pthread_keys | _thread_db___pthread_keys | libc.so.6 | — | not-started |
| GLIBC-_thread_db_const_thread_area | _thread_db_const_thread_area | libc.so.6 | — | not-started |
| GLIBC-_thread_db_dtv_dtv | _thread_db_dtv_dtv | libc.so.6 | — | not-started |
| GLIBC-_thread_db_dtv_slotinfo_gen | _thread_db_dtv_slotinfo_gen | libc.so.6 | — | not-started |
| GLIBC-_thread_db_dtv_slotinfo_list_len | _thread_db_dtv_slotinfo_list_len | libc.so.6 | — | not-started |
| GLIBC-_thread_db_dtv_slotinfo_list_next | _thread_db_dtv_slotinfo_list_next | libc.so.6 | — | not-started |
| GLIBC-_thread_db_dtv_slotinfo_list_slotinfo | _thread_db_dtv_slotinfo_list_slotinfo | libc.so.6 | — | not-started |
| GLIBC-_thread_db_dtv_slotinfo_map | _thread_db_dtv_slotinfo_map | libc.so.6 | — | not-started |
| GLIBC-_thread_db_dtv_t_counter | _thread_db_dtv_t_counter | libc.so.6 | — | not-started |
| GLIBC-_thread_db_dtv_t_pointer_val | _thread_db_dtv_t_pointer_val | libc.so.6 | — | not-started |
| GLIBC-_thread_db_link_map_l_tls_modid | _thread_db_link_map_l_tls_modid | libc.so.6 | — | not-started |
| GLIBC-_thread_db_link_map_l_tls_offset | _thread_db_link_map_l_tls_offset | libc.so.6 | — | not-started |
| GLIBC-_thread_db_list_t_next | _thread_db_list_t_next | libc.so.6 | — | not-started |
| GLIBC-_thread_db_list_t_prev | _thread_db_list_t_prev | libc.so.6 | — | not-started |
| GLIBC-_thread_db_pthread_cancelhandling | _thread_db_pthread_cancelhandling | libc.so.6 | — | not-started |
| GLIBC-_thread_db_pthread_dtvp | _thread_db_pthread_dtvp | libc.so.6 | — | not-started |
| GLIBC-_thread_db_pthread_eventbuf | _thread_db_pthread_eventbuf | libc.so.6 | — | not-started |
| GLIBC-_thread_db_pthread_eventbuf_eventmask | _thread_db_pthread_eventbuf_eventmask | libc.so.6 | — | not-started |
| GLIBC-_thread_db_pthread_eventbuf_eventmask_event_bits | _thread_db_pthread_eventbuf_eventmask_event_bits | libc.so.6 | — | not-started |
| GLIBC-_thread_db_pthread_key_data_data | _thread_db_pthread_key_data_data | libc.so.6 | — | not-started |
| GLIBC-_thread_db_pthread_key_data_level2_data | _thread_db_pthread_key_data_level2_data | libc.so.6 | — | not-started |
| GLIBC-_thread_db_pthread_key_data_seq | _thread_db_pthread_key_data_seq | libc.so.6 | — | not-started |
| GLIBC-_thread_db_pthread_key_struct_destr | _thread_db_pthread_key_struct_destr | libc.so.6 | — | not-started |
| GLIBC-_thread_db_pthread_key_struct_seq | _thread_db_pthread_key_struct_seq | libc.so.6 | — | not-started |
| GLIBC-_thread_db_pthread_list | _thread_db_pthread_list | libc.so.6 | — | not-started |
| GLIBC-_thread_db_pthread_nextevent | _thread_db_pthread_nextevent | libc.so.6 | — | not-started |
| GLIBC-_thread_db_pthread_report_events | _thread_db_pthread_report_events | libc.so.6 | — | not-started |
| GLIBC-_thread_db_pthread_schedparam_sched_priority | _thread_db_pthread_schedparam_sched_priority | libc.so.6 | — | not-started |
| GLIBC-_thread_db_pthread_schedpolicy | _thread_db_pthread_schedpolicy | libc.so.6 | — | not-started |
| GLIBC-_thread_db_pthread_specific | _thread_db_pthread_specific | libc.so.6 | — | not-started |
| GLIBC-_thread_db_pthread_start_routine | _thread_db_pthread_start_routine | libc.so.6 | — | not-started |
| GLIBC-_thread_db_pthread_tid | _thread_db_pthread_tid | libc.so.6 | — | not-started |
| GLIBC-_thread_db_rtld_global__dl_stack_used | _thread_db_rtld_global__dl_stack_used | libc.so.6 | — | not-started |
| GLIBC-_thread_db_rtld_global__dl_stack_user | _thread_db_rtld_global__dl_stack_user | libc.so.6 | — | not-started |
| GLIBC-_thread_db_rtld_global__dl_tls_dtv_slotinfo_list | _thread_db_rtld_global__dl_tls_dtv_slotinfo_list | libc.so.6 | — | not-started |
| GLIBC-_thread_db_sizeof_dtv_slotinfo | _thread_db_sizeof_dtv_slotinfo | libc.so.6 | — | not-started |
| GLIBC-_thread_db_sizeof_dtv_slotinfo_list | _thread_db_sizeof_dtv_slotinfo_list | libc.so.6 | — | not-started |
| GLIBC-_thread_db_sizeof_list_t | _thread_db_sizeof_list_t | libc.so.6 | — | not-started |
| GLIBC-_thread_db_sizeof_pthread | _thread_db_sizeof_pthread | libc.so.6 | — | not-started |
| GLIBC-_thread_db_sizeof_pthread_key_data | _thread_db_sizeof_pthread_key_data | libc.so.6 | — | not-started |
| GLIBC-_thread_db_sizeof_pthread_key_data_level2 | _thread_db_sizeof_pthread_key_data_level2 | libc.so.6 | — | not-started |
| GLIBC-_thread_db_sizeof_pthread_key_struct | _thread_db_sizeof_pthread_key_struct | libc.so.6 | — | not-started |
| GLIBC-_thread_db_sizeof_td_eventbuf_t | _thread_db_sizeof_td_eventbuf_t | libc.so.6 | — | not-started |
| GLIBC-_thread_db_sizeof_td_thr_events_t | _thread_db_sizeof_td_thr_events_t | libc.so.6 | — | not-started |
| GLIBC-_thread_db_td_eventbuf_t_eventdata | _thread_db_td_eventbuf_t_eventdata | libc.so.6 | — | not-started |
| GLIBC-_thread_db_td_eventbuf_t_eventnum | _thread_db_td_eventbuf_t_eventnum | libc.so.6 | — | not-started |
| GLIBC-_thread_db_td_thr_events_t_event_bits | _thread_db_td_thr_events_t_event_bits | libc.so.6 | — | not-started |
| GLIBC-accept4 | accept4 | libc.so.6 | — | documented; Grouped |
| GLIBC-acct | acct | libc.so.6 | — | not-started |
| GLIBC-acosf128 | acosf128 | libm.so.6 | — | not-started |
| GLIBC-acosf32 | acosf32 | libm.so.6 | — | not-started |
| GLIBC-acosf32x | acosf32x | libm.so.6 | — | not-started |
| GLIBC-acosf64 | acosf64 | libm.so.6 | — | not-started |
| GLIBC-acosf64x | acosf64x | libm.so.6 | — | not-started |
| GLIBC-acoshf128 | acoshf128 | libm.so.6 | — | not-started |
| GLIBC-acoshf32 | acoshf32 | libm.so.6 | — | not-started |
| GLIBC-acoshf32x | acoshf32x | libm.so.6 | — | not-started |
| GLIBC-acoshf64 | acoshf64 | libm.so.6 | — | not-started |
| GLIBC-acoshf64x | acoshf64x | libm.so.6 | — | not-started |
| GLIBC-acospif128 | acospif128 | libm.so.6 | — | not-started |
| GLIBC-acospif32 | acospif32 | libm.so.6 | — | not-started |
| GLIBC-acospif32x | acospif32x | libm.so.6 | — | not-started |
| GLIBC-acospif64 | acospif64 | libm.so.6 | — | not-started |
| GLIBC-acospif64x | acospif64x | libm.so.6 | — | not-started |
| GLIBC-advance | advance | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-arch_prctl | arch_prctl | libc.so.6 | — | not-started |
| GLIBC-argp_err_exit_status | argp_err_exit_status | libc.so.6 | — | not-started |
| GLIBC-argp_program_bug_address | argp_program_bug_address | libc.so.6 | — | not-started |
| GLIBC-argp_program_version | argp_program_version | libc.so.6 | — | not-started |
| GLIBC-argp_program_version_hook | argp_program_version_hook | libc.so.6 | — | not-started |
| GLIBC-asctime | asctime | libc.so.6 | — | researched; time |
| GLIBC-asctime_r | asctime_r | libc.so.6 | — | researched; time |
| GLIBC-asinf128 | asinf128 | libm.so.6 | — | not-started |
| GLIBC-asinf32 | asinf32 | libm.so.6 | — | not-started |
| GLIBC-asinf32x | asinf32x | libm.so.6 | — | not-started |
| GLIBC-asinf64 | asinf64 | libm.so.6 | — | not-started |
| GLIBC-asinf64x | asinf64x | libm.so.6 | — | not-started |
| GLIBC-asinhf128 | asinhf128 | libm.so.6 | — | not-started |
| GLIBC-asinhf32 | asinhf32 | libm.so.6 | — | not-started |
| GLIBC-asinhf32x | asinhf32x | libm.so.6 | — | not-started |
| GLIBC-asinhf64 | asinhf64 | libm.so.6 | — | not-started |
| GLIBC-asinhf64x | asinhf64x | libm.so.6 | — | not-started |
| GLIBC-asinpif128 | asinpif128 | libm.so.6 | — | not-started |
| GLIBC-asinpif32 | asinpif32 | libm.so.6 | — | not-started |
| GLIBC-asinpif32x | asinpif32x | libm.so.6 | — | not-started |
| GLIBC-asinpif64 | asinpif64 | libm.so.6 | — | not-started |
| GLIBC-asinpif64x | asinpif64x | libm.so.6 | — | not-started |
| GLIBC-atan2f128 | atan2f128 | libm.so.6 | — | not-started |
| GLIBC-atan2f32 | atan2f32 | libm.so.6 | — | not-started |
| GLIBC-atan2f32x | atan2f32x | libm.so.6 | — | not-started |
| GLIBC-atan2f64 | atan2f64 | libm.so.6 | — | not-started |
| GLIBC-atan2f64x | atan2f64x | libm.so.6 | — | not-started |
| GLIBC-atan2pif128 | atan2pif128 | libm.so.6 | — | not-started |
| GLIBC-atan2pif32 | atan2pif32 | libm.so.6 | — | not-started |
| GLIBC-atan2pif32x | atan2pif32x | libm.so.6 | — | not-started |
| GLIBC-atan2pif64 | atan2pif64 | libm.so.6 | — | not-started |
| GLIBC-atan2pif64x | atan2pif64x | libm.so.6 | — | not-started |
| GLIBC-atanf128 | atanf128 | libm.so.6 | — | not-started |
| GLIBC-atanf32 | atanf32 | libm.so.6 | — | not-started |
| GLIBC-atanf32x | atanf32x | libm.so.6 | — | not-started |
| GLIBC-atanf64 | atanf64 | libm.so.6 | — | not-started |
| GLIBC-atanf64x | atanf64x | libm.so.6 | — | not-started |
| GLIBC-atanhf128 | atanhf128 | libm.so.6 | — | not-started |
| GLIBC-atanhf32 | atanhf32 | libm.so.6 | — | not-started |
| GLIBC-atanhf32x | atanhf32x | libm.so.6 | — | not-started |
| GLIBC-atanhf64 | atanhf64 | libm.so.6 | — | not-started |
| GLIBC-atanhf64x | atanhf64x | libm.so.6 | — | not-started |
| GLIBC-atanpif128 | atanpif128 | libm.so.6 | — | not-started |
| GLIBC-atanpif32 | atanpif32 | libm.so.6 | — | not-started |
| GLIBC-atanpif32x | atanpif32x | libm.so.6 | — | not-started |
| GLIBC-atanpif64 | atanpif64 | libm.so.6 | — | not-started |
| GLIBC-atanpif64x | atanpif64x | libm.so.6 | — | not-started |
| GLIBC-authdes_create | authdes_create | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-authdes_getucred | authdes_getucred | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-authdes_pk_create | authdes_pk_create | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-authnone_create | authnone_create | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-authunix_create | authunix_create | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-authunix_create_default | authunix_create_default | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-bdflush | bdflush | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-bindresvport | bindresvport | libc.so.6 | — | researched; netdb |
| GLIBC-bsd_signal | bsd_signal | libc.so.6 | — | not-started |
| GLIBC-c16rtomb | c16rtomb | libc.so.6 | — | not-started |
| GLIBC-c32rtomb | c32rtomb | libc.so.6 | — | not-started |
| GLIBC-c8rtomb | c8rtomb | libc.so.6 | — | not-started |
| GLIBC-cabsf128 | cabsf128 | libm.so.6 | — | not-started |
| GLIBC-cabsf32 | cabsf32 | libm.so.6 | — | not-started |
| GLIBC-cabsf32x | cabsf32x | libm.so.6 | — | not-started |
| GLIBC-cabsf64 | cabsf64 | libm.so.6 | — | not-started |
| GLIBC-cabsf64x | cabsf64x | libm.so.6 | — | not-started |
| GLIBC-cacosf128 | cacosf128 | libm.so.6 | — | not-started |
| GLIBC-cacosf32 | cacosf32 | libm.so.6 | — | not-started |
| GLIBC-cacosf32x | cacosf32x | libm.so.6 | — | not-started |
| GLIBC-cacosf64 | cacosf64 | libm.so.6 | — | not-started |
| GLIBC-cacosf64x | cacosf64x | libm.so.6 | — | not-started |
| GLIBC-cacoshf128 | cacoshf128 | libm.so.6 | — | not-started |
| GLIBC-cacoshf32 | cacoshf32 | libm.so.6 | — | not-started |
| GLIBC-cacoshf32x | cacoshf32x | libm.so.6 | — | not-started |
| GLIBC-cacoshf64 | cacoshf64 | libm.so.6 | — | not-started |
| GLIBC-cacoshf64x | cacoshf64x | libm.so.6 | — | not-started |
| GLIBC-callrpc | callrpc | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-canonicalizef128 | canonicalizef128 | libm.so.6 | — | not-started |
| GLIBC-canonicalizef32 | canonicalizef32 | libm.so.6 | — | not-started |
| GLIBC-canonicalizef32x | canonicalizef32x | libm.so.6 | — | not-started |
| GLIBC-canonicalizef64 | canonicalizef64 | libm.so.6 | — | not-started |
| GLIBC-canonicalizef64x | canonicalizef64x | libm.so.6 | — | not-started |
| GLIBC-capget | capget | libc.so.6 | — | not-started |
| GLIBC-capset | capset | libc.so.6 | — | not-started |
| GLIBC-cargf128 | cargf128 | libm.so.6 | — | not-started |
| GLIBC-cargf32 | cargf32 | libm.so.6 | — | not-started |
| GLIBC-cargf32x | cargf32x | libm.so.6 | — | not-started |
| GLIBC-cargf64 | cargf64 | libm.so.6 | — | not-started |
| GLIBC-cargf64x | cargf64x | libm.so.6 | — | not-started |
| GLIBC-casinf128 | casinf128 | libm.so.6 | — | not-started |
| GLIBC-casinf32 | casinf32 | libm.so.6 | — | not-started |
| GLIBC-casinf32x | casinf32x | libm.so.6 | — | not-started |
| GLIBC-casinf64 | casinf64 | libm.so.6 | — | not-started |
| GLIBC-casinf64x | casinf64x | libm.so.6 | — | not-started |
| GLIBC-casinhf128 | casinhf128 | libm.so.6 | — | not-started |
| GLIBC-casinhf32 | casinhf32 | libm.so.6 | — | not-started |
| GLIBC-casinhf32x | casinhf32x | libm.so.6 | — | not-started |
| GLIBC-casinhf64 | casinhf64 | libm.so.6 | — | not-started |
| GLIBC-casinhf64x | casinhf64x | libm.so.6 | — | not-started |
| GLIBC-catanf128 | catanf128 | libm.so.6 | — | not-started |
| GLIBC-catanf32 | catanf32 | libm.so.6 | — | not-started |
| GLIBC-catanf32x | catanf32x | libm.so.6 | — | not-started |
| GLIBC-catanf64 | catanf64 | libm.so.6 | — | not-started |
| GLIBC-catanf64x | catanf64x | libm.so.6 | — | not-started |
| GLIBC-catanhf128 | catanhf128 | libm.so.6 | — | not-started |
| GLIBC-catanhf32 | catanhf32 | libm.so.6 | — | not-started |
| GLIBC-catanhf32x | catanhf32x | libm.so.6 | — | not-started |
| GLIBC-catanhf64 | catanhf64 | libm.so.6 | — | not-started |
| GLIBC-catanhf64x | catanhf64x | libm.so.6 | — | not-started |
| GLIBC-cbc_crypt | cbc_crypt | libc.so.6 | GLIBC_2.2.5 | researched; crypt |
| GLIBC-cbrtf128 | cbrtf128 | libm.so.6 | — | not-started |
| GLIBC-cbrtf32 | cbrtf32 | libm.so.6 | — | not-started |
| GLIBC-cbrtf32x | cbrtf32x | libm.so.6 | — | not-started |
| GLIBC-cbrtf64 | cbrtf64 | libm.so.6 | — | not-started |
| GLIBC-cbrtf64x | cbrtf64x | libm.so.6 | — | not-started |
| GLIBC-ccosf128 | ccosf128 | libm.so.6 | — | not-started |
| GLIBC-ccosf32 | ccosf32 | libm.so.6 | — | not-started |
| GLIBC-ccosf32x | ccosf32x | libm.so.6 | — | not-started |
| GLIBC-ccosf64 | ccosf64 | libm.so.6 | — | not-started |
| GLIBC-ccosf64x | ccosf64x | libm.so.6 | — | not-started |
| GLIBC-ccoshf128 | ccoshf128 | libm.so.6 | — | not-started |
| GLIBC-ccoshf32 | ccoshf32 | libm.so.6 | — | not-started |
| GLIBC-ccoshf32x | ccoshf32x | libm.so.6 | — | not-started |
| GLIBC-ccoshf64 | ccoshf64 | libm.so.6 | — | not-started |
| GLIBC-ccoshf64x | ccoshf64x | libm.so.6 | — | not-started |
| GLIBC-ceilf128 | ceilf128 | libm.so.6 | — | not-started |
| GLIBC-ceilf32 | ceilf32 | libm.so.6 | — | not-started |
| GLIBC-ceilf32x | ceilf32x | libm.so.6 | — | not-started |
| GLIBC-ceilf64 | ceilf64 | libm.so.6 | — | not-started |
| GLIBC-ceilf64x | ceilf64x | libm.so.6 | — | not-started |
| GLIBC-cexpf128 | cexpf128 | libm.so.6 | — | not-started |
| GLIBC-cexpf32 | cexpf32 | libm.so.6 | — | not-started |
| GLIBC-cexpf32x | cexpf32x | libm.so.6 | — | not-started |
| GLIBC-cexpf64 | cexpf64 | libm.so.6 | — | not-started |
| GLIBC-cexpf64x | cexpf64x | libm.so.6 | — | not-started |
| GLIBC-cfree | cfree | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-chflags | chflags | libc.so.6 | — | not-started |
| GLIBC-chroot | chroot | libc.so.6 | — | not-started |
| GLIBC-cimagf128 | cimagf128 | libm.so.6 | — | not-started |
| GLIBC-cimagf32 | cimagf32 | libm.so.6 | — | not-started |
| GLIBC-cimagf32x | cimagf32x | libm.so.6 | — | not-started |
| GLIBC-cimagf64 | cimagf64 | libm.so.6 | — | not-started |
| GLIBC-cimagf64x | cimagf64x | libm.so.6 | — | not-started |
| GLIBC-clnt_broadcast | clnt_broadcast | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-clnt_create | clnt_create | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-clnt_pcreateerror | clnt_pcreateerror | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-clnt_perrno | clnt_perrno | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-clnt_perror | clnt_perror | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-clnt_spcreateerror | clnt_spcreateerror | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-clnt_sperrno | clnt_sperrno | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-clnt_sperror | clnt_sperror | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-clntraw_create | clntraw_create | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-clnttcp_create | clnttcp_create | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-clntudp_bufcreate | clntudp_bufcreate | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-clntudp_create | clntudp_create | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-clntunix_create | clntunix_create | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-clock_adjtime | clock_adjtime | libc.so.6 | — | not-started |
| GLIBC-clock_getcpuclockid | clock_getcpuclockid | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-clog10f128 | clog10f128 | libm.so.6 | — | not-started |
| GLIBC-clog10f32 | clog10f32 | libm.so.6 | — | not-started |
| GLIBC-clog10f32x | clog10f32x | libm.so.6 | — | not-started |
| GLIBC-clog10f64 | clog10f64 | libm.so.6 | — | not-started |
| GLIBC-clog10f64x | clog10f64x | libm.so.6 | — | not-started |
| GLIBC-clogf128 | clogf128 | libm.so.6 | — | not-started |
| GLIBC-clogf32 | clogf32 | libm.so.6 | — | not-started |
| GLIBC-clogf32x | clogf32x | libm.so.6 | — | not-started |
| GLIBC-clogf64 | clogf64 | libm.so.6 | — | not-started |
| GLIBC-clogf64x | clogf64x | libm.so.6 | — | not-started |
| GLIBC-clone | clone | libc.so.6 | — | not-started |
| GLIBC-conjf128 | conjf128 | libm.so.6 | — | not-started |
| GLIBC-conjf32 | conjf32 | libm.so.6 | — | not-started |
| GLIBC-conjf32x | conjf32x | libm.so.6 | — | not-started |
| GLIBC-conjf64 | conjf64 | libm.so.6 | — | not-started |
| GLIBC-conjf64x | conjf64x | libm.so.6 | — | not-started |
| GLIBC-copysignf128 | copysignf128 | libm.so.6 | — | not-started |
| GLIBC-copysignf32 | copysignf32 | libm.so.6 | — | not-started |
| GLIBC-copysignf32x | copysignf32x | libm.so.6 | — | not-started |
| GLIBC-copysignf64 | copysignf64 | libm.so.6 | — | not-started |
| GLIBC-copysignf64x | copysignf64x | libm.so.6 | — | not-started |
| GLIBC-cosf128 | cosf128 | libm.so.6 | — | not-started |
| GLIBC-cosf32 | cosf32 | libm.so.6 | — | not-started |
| GLIBC-cosf32x | cosf32x | libm.so.6 | — | not-started |
| GLIBC-cosf64 | cosf64 | libm.so.6 | — | not-started |
| GLIBC-cosf64x | cosf64x | libm.so.6 | — | not-started |
| GLIBC-coshf128 | coshf128 | libm.so.6 | — | not-started |
| GLIBC-coshf32 | coshf32 | libm.so.6 | — | not-started |
| GLIBC-coshf32x | coshf32x | libm.so.6 | — | not-started |
| GLIBC-coshf64 | coshf64 | libm.so.6 | — | not-started |
| GLIBC-coshf64x | coshf64x | libm.so.6 | — | not-started |
| GLIBC-cospif128 | cospif128 | libm.so.6 | — | not-started |
| GLIBC-cospif32 | cospif32 | libm.so.6 | — | not-started |
| GLIBC-cospif32x | cospif32x | libm.so.6 | — | not-started |
| GLIBC-cospif64 | cospif64 | libm.so.6 | — | not-started |
| GLIBC-cospif64x | cospif64x | libm.so.6 | — | not-started |
| GLIBC-cpowf128 | cpowf128 | libm.so.6 | — | not-started |
| GLIBC-cpowf32 | cpowf32 | libm.so.6 | — | not-started |
| GLIBC-cpowf32x | cpowf32x | libm.so.6 | — | not-started |
| GLIBC-cpowf64 | cpowf64 | libm.so.6 | — | not-started |
| GLIBC-cpowf64x | cpowf64x | libm.so.6 | — | not-started |
| GLIBC-cprojf128 | cprojf128 | libm.so.6 | — | not-started |
| GLIBC-cprojf32 | cprojf32 | libm.so.6 | — | not-started |
| GLIBC-cprojf32x | cprojf32x | libm.so.6 | — | not-started |
| GLIBC-cprojf64 | cprojf64 | libm.so.6 | — | not-started |
| GLIBC-cprojf64x | cprojf64x | libm.so.6 | — | not-started |
| GLIBC-crealf128 | crealf128 | libm.so.6 | — | not-started |
| GLIBC-crealf32 | crealf32 | libm.so.6 | — | not-started |
| GLIBC-crealf32x | crealf32x | libm.so.6 | — | not-started |
| GLIBC-crealf64 | crealf64 | libm.so.6 | — | not-started |
| GLIBC-crealf64x | crealf64x | libm.so.6 | — | not-started |
| GLIBC-creat | creat | libc.so.6 | — | not-started |
| GLIBC-creat64 | creat64 | libc.so.6 | — | not-started |
| GLIBC-create_module | create_module | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-crypt | crypt | libcrypt.so.1 | GLIBC_2.2.5 | researched; cryptographic; musl-catalog |
| GLIBC-crypt_checksalt | crypt_checksalt | libcrypt.so.1 | — | not-started |
| GLIBC-crypt_gensalt | crypt_gensalt | libcrypt.so.1 | — | not-started |
| GLIBC-crypt_gensalt_r | crypt_gensalt_r | libcrypt.so.1 | — | not-started |
| GLIBC-crypt_gensalt_ra | crypt_gensalt_ra | libcrypt.so.1 | — | not-started |
| GLIBC-crypt_gensalt_rn | crypt_gensalt_rn | libcrypt.so.1 | — | not-started |
| GLIBC-crypt_preferred_method | crypt_preferred_method | libcrypt.so.1 | — | not-started |
| GLIBC-crypt_r | crypt_r | libcrypt.so.1 | GLIBC_2.2.5 | researched; cryptographic |
| GLIBC-crypt_ra | crypt_ra | libcrypt.so.1 | — | not-started |
| GLIBC-crypt_rn | crypt_rn | libcrypt.so.1 | — | not-started |
| GLIBC-csinf128 | csinf128 | libm.so.6 | — | not-started |
| GLIBC-csinf32 | csinf32 | libm.so.6 | — | not-started |
| GLIBC-csinf32x | csinf32x | libm.so.6 | — | not-started |
| GLIBC-csinf64 | csinf64 | libm.so.6 | — | not-started |
| GLIBC-csinf64x | csinf64x | libm.so.6 | — | not-started |
| GLIBC-csinhf128 | csinhf128 | libm.so.6 | — | not-started |
| GLIBC-csinhf32 | csinhf32 | libm.so.6 | — | not-started |
| GLIBC-csinhf32x | csinhf32x | libm.so.6 | — | not-started |
| GLIBC-csinhf64 | csinhf64 | libm.so.6 | — | not-started |
| GLIBC-csinhf64x | csinhf64x | libm.so.6 | — | not-started |
| GLIBC-csqrtf128 | csqrtf128 | libm.so.6 | — | not-started |
| GLIBC-csqrtf32 | csqrtf32 | libm.so.6 | — | not-started |
| GLIBC-csqrtf32x | csqrtf32x | libm.so.6 | — | not-started |
| GLIBC-csqrtf64 | csqrtf64 | libm.so.6 | — | not-started |
| GLIBC-csqrtf64x | csqrtf64x | libm.so.6 | — | not-started |
| GLIBC-ctanf128 | ctanf128 | libm.so.6 | — | not-started |
| GLIBC-ctanf32 | ctanf32 | libm.so.6 | — | not-started |
| GLIBC-ctanf32x | ctanf32x | libm.so.6 | — | not-started |
| GLIBC-ctanf64 | ctanf64 | libm.so.6 | — | not-started |
| GLIBC-ctanf64x | ctanf64x | libm.so.6 | — | not-started |
| GLIBC-ctanhf128 | ctanhf128 | libm.so.6 | — | not-started |
| GLIBC-ctanhf32 | ctanhf32 | libm.so.6 | — | not-started |
| GLIBC-ctanhf32x | ctanhf32x | libm.so.6 | — | not-started |
| GLIBC-ctanhf64 | ctanhf64 | libm.so.6 | — | not-started |
| GLIBC-ctanhf64x | ctanhf64x | libm.so.6 | — | not-started |
| GLIBC-ctime | ctime | libc.so.6 | — | researched; time |
| GLIBC-ctime_r | ctime_r | libc.so.6 | — | researched; time |
| GLIBC-daemon | daemon | libc.so.6 | — | not-started |
| GLIBC-delete_module | delete_module | libc.so.6 | — | not-started |
| GLIBC-des_setparity | des_setparity | libc.so.6 | GLIBC_2.2.5 | researched; crypt |
| GLIBC-dl_iterate_phdr | dl_iterate_phdr | libc.so.6 | — | documented; FULL |
| GLIBC-dladdr | dladdr | libc.so.6 | GLIBC_2.2.5 | documented; Grouped |
| GLIBC-dladdr1 | dladdr1 | libc.so.6 | GLIBC_2.3.3 | documented; Grouped |
| GLIBC-dlclose | dlclose | libc.so.6 | GLIBC_2.2.5 | documented; FULL |
| GLIBC-dlerror | dlerror | libc.so.6 | GLIBC_2.2.5 | documented; FULL |
| GLIBC-dlmopen | dlmopen | libc.so.6 | GLIBC_2.3.4 | documented; Grouped |
| GLIBC-dlopen | dlopen | libc.so.6 | GLIBC_2.2.5 | documented; FULL |
| GLIBC-dlsym | dlsym | libc.so.6 | GLIBC_2.2.5 | documented; FULL |
| GLIBC-dlvsym | dlvsym | libc.so.6 | GLIBC_2.2.5 | documented; Grouped |
| GLIBC-dn_comp | dn_comp | libc.so.6 | — | not-started |
| GLIBC-dn_expand | dn_expand | libc.so.6 | — | not-started |
| GLIBC-dn_skipname | dn_skipname | libc.so.6 | — | not-started |
| GLIBC-duplocale | duplocale | libc.so.6 | — | documented; Grouped |
| GLIBC-dysize | dysize | libc.so.6 | — | not-started |
| GLIBC-eaccess | eaccess | libc.so.6 | — | not-started |
| GLIBC-ecb_crypt | ecb_crypt | libc.so.6 | GLIBC_2.2.5 | researched; crypt |
| GLIBC-encrypt | encrypt | libcrypt.so.1 | GLIBC_2.2.5 | researched; cryptographic |
| GLIBC-encrypt_r | encrypt_r | libcrypt.so.1 | GLIBC_2.2.5 | researched; cryptographic |
| GLIBC-endaliasent | endaliasent | libc.so.6 | — | not-started |
| GLIBC-endrpcent | endrpcent | libc.so.6 | — | not-started |
| GLIBC-endsgent | endsgent | libc.so.6 | — | not-started |
| GLIBC-endspent | endspent | libc.so.6 | — | not-started |
| GLIBC-endttyent | endttyent | libc.so.6 | — | not-started |
| GLIBC-endusershell | endusershell | libc.so.6 | — | not-started |
| GLIBC-epoll_create1 | epoll_create1 | libc.so.6 | — | not-started |
| GLIBC-epoll_ctl | epoll_ctl | libc.so.6 | — | not-started |
| GLIBC-epoll_pwait | epoll_pwait | libc.so.6 | — | not-started |
| GLIBC-epoll_pwait2 | epoll_pwait2 | libc.so.6 | — | not-started |
| GLIBC-erfcf128 | erfcf128 | libm.so.6 | — | not-started |
| GLIBC-erfcf32 | erfcf32 | libm.so.6 | — | not-started |
| GLIBC-erfcf32x | erfcf32x | libm.so.6 | — | not-started |
| GLIBC-erfcf64 | erfcf64 | libm.so.6 | — | not-started |
| GLIBC-erfcf64x | erfcf64x | libm.so.6 | — | not-started |
| GLIBC-erff128 | erff128 | libm.so.6 | — | not-started |
| GLIBC-erff32 | erff32 | libm.so.6 | — | not-started |
| GLIBC-erff32x | erff32x | libm.so.6 | — | not-started |
| GLIBC-erff64 | erff64 | libm.so.6 | — | not-started |
| GLIBC-erff64x | erff64x | libm.so.6 | — | not-started |
| GLIBC-errno | errno | libc.so.6 | — | documented; errno |
| GLIBC-error_message_count | error_message_count | libc.so.6 | — | documented; error/error_at_line |
| GLIBC-error_one_per_line | error_one_per_line | libc.so.6 | — | documented; error/error_at_line |
| GLIBC-error_print_progname | error_print_progname | libc.so.6 | — | documented; error/error_at_line |
| GLIBC-ether_aton | ether_aton | libc.so.6 | — | not-started |
| GLIBC-ether_aton_r | ether_aton_r | libc.so.6 | — | not-started |
| GLIBC-ether_hostton | ether_hostton | libc.so.6 | — | not-started |
| GLIBC-ether_line | ether_line | libc.so.6 | — | not-started |
| GLIBC-ether_ntoa | ether_ntoa | libc.so.6 | — | not-started |
| GLIBC-ether_ntoa_r | ether_ntoa_r | libc.so.6 | — | not-started |
| GLIBC-ether_ntohost | ether_ntohost | libc.so.6 | — | not-started |
| GLIBC-euidaccess | euidaccess | libc.so.6 | — | not-started |
| GLIBC-eventfd | eventfd | libc.so.6 | — | not-started |
| GLIBC-eventfd_read | eventfd_read | libc.so.6 | — | not-started |
| GLIBC-eventfd_write | eventfd_write | libc.so.6 | — | not-started |
| GLIBC-execveat | execveat | libc.so.6 | — | not-started |
| GLIBC-execvpe | execvpe | libc.so.6 | — | documented; triage |
| GLIBC-exp10f128 | exp10f128 | libm.so.6 | — | not-started |
| GLIBC-exp10f32 | exp10f32 | libm.so.6 | — | not-started |
| GLIBC-exp10f32x | exp10f32x | libm.so.6 | — | not-started |
| GLIBC-exp10f64 | exp10f64 | libm.so.6 | — | not-started |
| GLIBC-exp10f64x | exp10f64x | libm.so.6 | — | not-started |
| GLIBC-exp10m1f128 | exp10m1f128 | libm.so.6 | — | not-started |
| GLIBC-exp10m1f32 | exp10m1f32 | libm.so.6 | — | not-started |
| GLIBC-exp10m1f32x | exp10m1f32x | libm.so.6 | — | not-started |
| GLIBC-exp10m1f64 | exp10m1f64 | libm.so.6 | — | not-started |
| GLIBC-exp10m1f64x | exp10m1f64x | libm.so.6 | — | not-started |
| GLIBC-exp2f128 | exp2f128 | libm.so.6 | — | not-started |
| GLIBC-exp2f32 | exp2f32 | libm.so.6 | — | not-started |
| GLIBC-exp2f32x | exp2f32x | libm.so.6 | — | not-started |
| GLIBC-exp2f64 | exp2f64 | libm.so.6 | — | not-started |
| GLIBC-exp2f64x | exp2f64x | libm.so.6 | — | not-started |
| GLIBC-exp2m1f128 | exp2m1f128 | libm.so.6 | — | not-started |
| GLIBC-exp2m1f32 | exp2m1f32 | libm.so.6 | — | not-started |
| GLIBC-exp2m1f32x | exp2m1f32x | libm.so.6 | — | not-started |
| GLIBC-exp2m1f64 | exp2m1f64 | libm.so.6 | — | not-started |
| GLIBC-exp2m1f64x | exp2m1f64x | libm.so.6 | — | not-started |
| GLIBC-expf128 | expf128 | libm.so.6 | — | not-started |
| GLIBC-expf32 | expf32 | libm.so.6 | — | not-started |
| GLIBC-expf32x | expf32x | libm.so.6 | — | not-started |
| GLIBC-expf64 | expf64 | libm.so.6 | — | not-started |
| GLIBC-expf64x | expf64x | libm.so.6 | — | not-started |
| GLIBC-expm1f128 | expm1f128 | libm.so.6 | — | not-started |
| GLIBC-expm1f32 | expm1f32 | libm.so.6 | — | not-started |
| GLIBC-expm1f32x | expm1f32x | libm.so.6 | — | not-started |
| GLIBC-expm1f64 | expm1f64 | libm.so.6 | — | not-started |
| GLIBC-expm1f64x | expm1f64x | libm.so.6 | — | not-started |
| GLIBC-f32addf128 | f32addf128 | libm.so.6 | — | not-started |
| GLIBC-f32addf32x | f32addf32x | libm.so.6 | — | not-started |
| GLIBC-f32addf64 | f32addf64 | libm.so.6 | — | not-started |
| GLIBC-f32addf64x | f32addf64x | libm.so.6 | — | not-started |
| GLIBC-f32divf128 | f32divf128 | libm.so.6 | — | not-started |
| GLIBC-f32divf32x | f32divf32x | libm.so.6 | — | not-started |
| GLIBC-f32divf64 | f32divf64 | libm.so.6 | — | not-started |
| GLIBC-f32divf64x | f32divf64x | libm.so.6 | — | not-started |
| GLIBC-f32fmaf128 | f32fmaf128 | libm.so.6 | — | not-started |
| GLIBC-f32fmaf32x | f32fmaf32x | libm.so.6 | — | not-started |
| GLIBC-f32fmaf64 | f32fmaf64 | libm.so.6 | — | not-started |
| GLIBC-f32fmaf64x | f32fmaf64x | libm.so.6 | — | not-started |
| GLIBC-f32mulf128 | f32mulf128 | libm.so.6 | — | not-started |
| GLIBC-f32mulf32x | f32mulf32x | libm.so.6 | — | not-started |
| GLIBC-f32mulf64 | f32mulf64 | libm.so.6 | — | not-started |
| GLIBC-f32mulf64x | f32mulf64x | libm.so.6 | — | not-started |
| GLIBC-f32sqrtf128 | f32sqrtf128 | libm.so.6 | — | not-started |
| GLIBC-f32sqrtf32x | f32sqrtf32x | libm.so.6 | — | not-started |
| GLIBC-f32sqrtf64 | f32sqrtf64 | libm.so.6 | — | not-started |
| GLIBC-f32sqrtf64x | f32sqrtf64x | libm.so.6 | — | not-started |
| GLIBC-f32subf128 | f32subf128 | libm.so.6 | — | not-started |
| GLIBC-f32subf32x | f32subf32x | libm.so.6 | — | not-started |
| GLIBC-f32subf64 | f32subf64 | libm.so.6 | — | not-started |
| GLIBC-f32subf64x | f32subf64x | libm.so.6 | — | not-started |
| GLIBC-f32xaddf128 | f32xaddf128 | libm.so.6 | — | not-started |
| GLIBC-f32xaddf64 | f32xaddf64 | libm.so.6 | — | not-started |
| GLIBC-f32xaddf64x | f32xaddf64x | libm.so.6 | — | not-started |
| GLIBC-f32xdivf128 | f32xdivf128 | libm.so.6 | — | not-started |
| GLIBC-f32xdivf64 | f32xdivf64 | libm.so.6 | — | not-started |
| GLIBC-f32xdivf64x | f32xdivf64x | libm.so.6 | — | not-started |
| GLIBC-f32xfmaf128 | f32xfmaf128 | libm.so.6 | — | not-started |
| GLIBC-f32xfmaf64 | f32xfmaf64 | libm.so.6 | — | not-started |
| GLIBC-f32xfmaf64x | f32xfmaf64x | libm.so.6 | — | not-started |
| GLIBC-f32xmulf128 | f32xmulf128 | libm.so.6 | — | not-started |
| GLIBC-f32xmulf64 | f32xmulf64 | libm.so.6 | — | not-started |
| GLIBC-f32xmulf64x | f32xmulf64x | libm.so.6 | — | not-started |
| GLIBC-f32xsqrtf128 | f32xsqrtf128 | libm.so.6 | — | not-started |
| GLIBC-f32xsqrtf64 | f32xsqrtf64 | libm.so.6 | — | not-started |
| GLIBC-f32xsqrtf64x | f32xsqrtf64x | libm.so.6 | — | not-started |
| GLIBC-f32xsubf128 | f32xsubf128 | libm.so.6 | — | not-started |
| GLIBC-f32xsubf64 | f32xsubf64 | libm.so.6 | — | not-started |
| GLIBC-f32xsubf64x | f32xsubf64x | libm.so.6 | — | not-started |
| GLIBC-f64addf128 | f64addf128 | libm.so.6 | — | not-started |
| GLIBC-f64addf64x | f64addf64x | libm.so.6 | — | not-started |
| GLIBC-f64divf128 | f64divf128 | libm.so.6 | — | not-started |
| GLIBC-f64divf64x | f64divf64x | libm.so.6 | — | not-started |
| GLIBC-f64fmaf128 | f64fmaf128 | libm.so.6 | — | not-started |
| GLIBC-f64fmaf64x | f64fmaf64x | libm.so.6 | — | not-started |
| GLIBC-f64mulf128 | f64mulf128 | libm.so.6 | — | not-started |
| GLIBC-f64mulf64x | f64mulf64x | libm.so.6 | — | not-started |
| GLIBC-f64sqrtf128 | f64sqrtf128 | libm.so.6 | — | not-started |
| GLIBC-f64sqrtf64x | f64sqrtf64x | libm.so.6 | — | not-started |
| GLIBC-f64subf128 | f64subf128 | libm.so.6 | — | not-started |
| GLIBC-f64subf64x | f64subf64x | libm.so.6 | — | not-started |
| GLIBC-f64xaddf128 | f64xaddf128 | libm.so.6 | — | not-started |
| GLIBC-f64xdivf128 | f64xdivf128 | libm.so.6 | — | not-started |
| GLIBC-f64xfmaf128 | f64xfmaf128 | libm.so.6 | — | not-started |
| GLIBC-f64xmulf128 | f64xmulf128 | libm.so.6 | — | not-started |
| GLIBC-f64xsqrtf128 | f64xsqrtf128 | libm.so.6 | — | not-started |
| GLIBC-f64xsubf128 | f64xsubf128 | libm.so.6 | — | not-started |
| GLIBC-fabsf128 | fabsf128 | libm.so.6 | — | not-started |
| GLIBC-fabsf32 | fabsf32 | libm.so.6 | — | not-started |
| GLIBC-fabsf32x | fabsf32x | libm.so.6 | — | not-started |
| GLIBC-fabsf64 | fabsf64 | libm.so.6 | — | not-started |
| GLIBC-fabsf64x | fabsf64x | libm.so.6 | — | not-started |
| GLIBC-fallocate | fallocate | libc.so.6 | — | not-started |
| GLIBC-fallocate64 | fallocate64 | libc.so.6 | — | not-started |
| GLIBC-fanotify_init | fanotify_init | libc.so.6 | — | not-started |
| GLIBC-fanotify_mark | fanotify_mark | libc.so.6 | — | not-started |
| GLIBC-fattach | fattach | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-fchflags | fchflags | libc.so.6 | — | not-started |
| GLIBC-fchmodat | fchmodat | libc.so.6 | — | not-started |
| GLIBC-fchownat | fchownat | libc.so.6 | — | not-started |
| GLIBC-fcntl64 | fcntl64 | libc.so.6 | — | not-started |
| GLIBC-fcrypt | fcrypt | libcrypt.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-fdetach | fdetach | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-fdimf128 | fdimf128 | libm.so.6 | — | not-started |
| GLIBC-fdimf32 | fdimf32 | libm.so.6 | — | not-started |
| GLIBC-fdimf32x | fdimf32x | libm.so.6 | — | not-started |
| GLIBC-fdimf64 | fdimf64 | libm.so.6 | — | not-started |
| GLIBC-fdimf64x | fdimf64x | libm.so.6 | — | not-started |
| GLIBC-ffs | ffs | libc.so.6 | — | researched; string.h |
| GLIBC-ffsl | ffsl | libc.so.6 | — | researched; string.h |
| GLIBC-ffsll | ffsll | libc.so.6 | — | researched; string.h |
| GLIBC-fgetsgent | fgetsgent | libc.so.6 | — | not-started |
| GLIBC-fgetsgent_r | fgetsgent_r | libc.so.6 | — | not-started |
| GLIBC-fgetspent | fgetspent | libc.so.6 | — | not-started |
| GLIBC-fgetspent_r | fgetspent_r | libc.so.6 | — | not-started |
| GLIBC-fgetxattr | fgetxattr | libc.so.6 | — | not-started |
| GLIBC-flistxattr | flistxattr | libc.so.6 | — | not-started |
| GLIBC-flock | flock | libc.so.6 | — | not-started |
| GLIBC-floorf128 | floorf128 | libm.so.6 | — | not-started |
| GLIBC-floorf32 | floorf32 | libm.so.6 | — | not-started |
| GLIBC-floorf32x | floorf32x | libm.so.6 | — | not-started |
| GLIBC-floorf64 | floorf64 | libm.so.6 | — | not-started |
| GLIBC-floorf64x | floorf64x | libm.so.6 | — | not-started |
| GLIBC-fmaf128 | fmaf128 | libm.so.6 | — | not-started |
| GLIBC-fmaf32 | fmaf32 | libm.so.6 | — | not-started |
| GLIBC-fmaf32x | fmaf32x | libm.so.6 | — | not-started |
| GLIBC-fmaf64 | fmaf64 | libm.so.6 | — | not-started |
| GLIBC-fmaf64x | fmaf64x | libm.so.6 | — | not-started |
| GLIBC-fmaxf128 | fmaxf128 | libm.so.6 | — | not-started |
| GLIBC-fmaxf32 | fmaxf32 | libm.so.6 | — | not-started |
| GLIBC-fmaxf32x | fmaxf32x | libm.so.6 | — | not-started |
| GLIBC-fmaxf64 | fmaxf64 | libm.so.6 | — | not-started |
| GLIBC-fmaxf64x | fmaxf64x | libm.so.6 | — | not-started |
| GLIBC-fmaximum_mag_numf128 | fmaximum_mag_numf128 | libm.so.6 | — | not-started |
| GLIBC-fmaximum_mag_numf32 | fmaximum_mag_numf32 | libm.so.6 | — | not-started |
| GLIBC-fmaximum_mag_numf32x | fmaximum_mag_numf32x | libm.so.6 | — | not-started |
| GLIBC-fmaximum_mag_numf64 | fmaximum_mag_numf64 | libm.so.6 | — | not-started |
| GLIBC-fmaximum_mag_numf64x | fmaximum_mag_numf64x | libm.so.6 | — | not-started |
| GLIBC-fmaximum_magf128 | fmaximum_magf128 | libm.so.6 | — | not-started |
| GLIBC-fmaximum_magf32 | fmaximum_magf32 | libm.so.6 | — | not-started |
| GLIBC-fmaximum_magf32x | fmaximum_magf32x | libm.so.6 | — | not-started |
| GLIBC-fmaximum_magf64 | fmaximum_magf64 | libm.so.6 | — | not-started |
| GLIBC-fmaximum_magf64x | fmaximum_magf64x | libm.so.6 | — | not-started |
| GLIBC-fmaximum_numf128 | fmaximum_numf128 | libm.so.6 | — | not-started |
| GLIBC-fmaximum_numf32 | fmaximum_numf32 | libm.so.6 | — | not-started |
| GLIBC-fmaximum_numf32x | fmaximum_numf32x | libm.so.6 | — | not-started |
| GLIBC-fmaximum_numf64 | fmaximum_numf64 | libm.so.6 | — | not-started |
| GLIBC-fmaximum_numf64x | fmaximum_numf64x | libm.so.6 | — | not-started |
| GLIBC-fmaximumf128 | fmaximumf128 | libm.so.6 | — | not-started |
| GLIBC-fmaximumf32 | fmaximumf32 | libm.so.6 | — | not-started |
| GLIBC-fmaximumf32x | fmaximumf32x | libm.so.6 | — | not-started |
| GLIBC-fmaximumf64 | fmaximumf64 | libm.so.6 | — | not-started |
| GLIBC-fmaximumf64x | fmaximumf64x | libm.so.6 | — | not-started |
| GLIBC-fmaxmagf128 | fmaxmagf128 | libm.so.6 | — | not-started |
| GLIBC-fmaxmagf32 | fmaxmagf32 | libm.so.6 | — | not-started |
| GLIBC-fmaxmagf32x | fmaxmagf32x | libm.so.6 | — | not-started |
| GLIBC-fmaxmagf64 | fmaxmagf64 | libm.so.6 | — | not-started |
| GLIBC-fmaxmagf64x | fmaxmagf64x | libm.so.6 | — | not-started |
| GLIBC-fminf128 | fminf128 | libm.so.6 | — | not-started |
| GLIBC-fminf32 | fminf32 | libm.so.6 | — | not-started |
| GLIBC-fminf32x | fminf32x | libm.so.6 | — | not-started |
| GLIBC-fminf64 | fminf64 | libm.so.6 | — | not-started |
| GLIBC-fminf64x | fminf64x | libm.so.6 | — | not-started |
| GLIBC-fminimum_mag_numf128 | fminimum_mag_numf128 | libm.so.6 | — | not-started |
| GLIBC-fminimum_mag_numf32 | fminimum_mag_numf32 | libm.so.6 | — | not-started |
| GLIBC-fminimum_mag_numf32x | fminimum_mag_numf32x | libm.so.6 | — | not-started |
| GLIBC-fminimum_mag_numf64 | fminimum_mag_numf64 | libm.so.6 | — | not-started |
| GLIBC-fminimum_mag_numf64x | fminimum_mag_numf64x | libm.so.6 | — | not-started |
| GLIBC-fminimum_magf128 | fminimum_magf128 | libm.so.6 | — | not-started |
| GLIBC-fminimum_magf32 | fminimum_magf32 | libm.so.6 | — | not-started |
| GLIBC-fminimum_magf32x | fminimum_magf32x | libm.so.6 | — | not-started |
| GLIBC-fminimum_magf64 | fminimum_magf64 | libm.so.6 | — | not-started |
| GLIBC-fminimum_magf64x | fminimum_magf64x | libm.so.6 | — | not-started |
| GLIBC-fminimum_numf128 | fminimum_numf128 | libm.so.6 | — | not-started |
| GLIBC-fminimum_numf32 | fminimum_numf32 | libm.so.6 | — | not-started |
| GLIBC-fminimum_numf32x | fminimum_numf32x | libm.so.6 | — | not-started |
| GLIBC-fminimum_numf64 | fminimum_numf64 | libm.so.6 | — | not-started |
| GLIBC-fminimum_numf64x | fminimum_numf64x | libm.so.6 | — | not-started |
| GLIBC-fminimumf128 | fminimumf128 | libm.so.6 | — | not-started |
| GLIBC-fminimumf32 | fminimumf32 | libm.so.6 | — | not-started |
| GLIBC-fminimumf32x | fminimumf32x | libm.so.6 | — | not-started |
| GLIBC-fminimumf64 | fminimumf64 | libm.so.6 | — | not-started |
| GLIBC-fminimumf64x | fminimumf64x | libm.so.6 | — | not-started |
| GLIBC-fminmagf128 | fminmagf128 | libm.so.6 | — | not-started |
| GLIBC-fminmagf32 | fminmagf32 | libm.so.6 | — | not-started |
| GLIBC-fminmagf32x | fminmagf32x | libm.so.6 | — | not-started |
| GLIBC-fminmagf64 | fminmagf64 | libm.so.6 | — | not-started |
| GLIBC-fminmagf64x | fminmagf64x | libm.so.6 | — | not-started |
| GLIBC-fmodf128 | fmodf128 | libm.so.6 | — | not-started |
| GLIBC-fmodf32 | fmodf32 | libm.so.6 | — | not-started |
| GLIBC-fmodf32x | fmodf32x | libm.so.6 | — | not-started |
| GLIBC-fmodf64 | fmodf64 | libm.so.6 | — | not-started |
| GLIBC-fmodf64x | fmodf64x | libm.so.6 | — | not-started |
| GLIBC-freeaddrinfo | freeaddrinfo | libc.so.6 | — | documented; Grouped |
| GLIBC-freeifaddrs | freeifaddrs | libc.so.6 | — | not-started |
| GLIBC-freelocale | freelocale | libc.so.6 | — | documented; Grouped |
| GLIBC-fremovexattr | fremovexattr | libc.so.6 | — | not-started |
| GLIBC-frexpf128 | frexpf128 | libm.so.6 | — | not-started |
| GLIBC-frexpf32 | frexpf32 | libm.so.6 | — | not-started |
| GLIBC-frexpf32x | frexpf32x | libm.so.6 | — | not-started |
| GLIBC-frexpf64 | frexpf64 | libm.so.6 | — | not-started |
| GLIBC-frexpf64x | frexpf64x | libm.so.6 | — | not-started |
| GLIBC-fromfpf128 | fromfpf128 | libm.so.6 | — | not-started |
| GLIBC-fromfpf32 | fromfpf32 | libm.so.6 | — | not-started |
| GLIBC-fromfpf32x | fromfpf32x | libm.so.6 | — | not-started |
| GLIBC-fromfpf64 | fromfpf64 | libm.so.6 | — | not-started |
| GLIBC-fromfpf64x | fromfpf64x | libm.so.6 | — | not-started |
| GLIBC-fromfpxf128 | fromfpxf128 | libm.so.6 | — | not-started |
| GLIBC-fromfpxf32 | fromfpxf32 | libm.so.6 | — | not-started |
| GLIBC-fromfpxf32x | fromfpxf32x | libm.so.6 | — | not-started |
| GLIBC-fromfpxf64 | fromfpxf64 | libm.so.6 | — | not-started |
| GLIBC-fromfpxf64x | fromfpxf64x | libm.so.6 | — | not-started |
| GLIBC-fsconfig | fsconfig | libc.so.6 | — | not-started |
| GLIBC-fsetxattr | fsetxattr | libc.so.6 | — | not-started |
| GLIBC-fsmount | fsmount | libc.so.6 | — | not-started |
| GLIBC-fsopen | fsopen | libc.so.6 | — | not-started |
| GLIBC-fspick | fspick | libc.so.6 | — | not-started |
| GLIBC-fstatfs | fstatfs | libc.so.6 | — | not-started |
| GLIBC-fstatfs64 | fstatfs64 | libc.so.6 | — | not-started |
| GLIBC-fstatvfs | fstatvfs | libc.so.6 | — | not-started |
| GLIBC-fstatvfs64 | fstatvfs64 | libc.so.6 | — | not-started |
| GLIBC-ftime | ftime | libc.so.6 | — | researched; time |
| GLIBC-ftok | ftok | libc.so.6 | — | documented; FULL |
| GLIBC-fts64_children | fts64_children | libc.so.6 | — | not-started |
| GLIBC-fts64_close | fts64_close | libc.so.6 | — | not-started |
| GLIBC-fts64_open | fts64_open | libc.so.6 | — | not-started |
| GLIBC-fts64_read | fts64_read | libc.so.6 | — | not-started |
| GLIBC-fts64_set | fts64_set | libc.so.6 | — | not-started |
| GLIBC-fts_children | fts_children | libc.so.6 | — | not-started |
| GLIBC-fts_close | fts_close | libc.so.6 | — | not-started |
| GLIBC-fts_open | fts_open | libc.so.6 | — | not-started |
| GLIBC-fts_read | fts_read | libc.so.6 | — | not-started |
| GLIBC-fts_set | fts_set | libc.so.6 | — | not-started |
| GLIBC-futimesat | futimesat | libc.so.6 | — | not-started |
| GLIBC-gai_cancel | gai_cancel | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-gai_error | gai_error | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-gai_strerror | gai_strerror | libc.so.6 | — | documented; Grouped |
| GLIBC-gai_suspend | gai_suspend | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-get_kernel_syms | get_kernel_syms | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-get_myaddress | get_myaddress | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-getaddrinfo | getaddrinfo | libc.so.6 | — | documented; FULL |
| GLIBC-getaddrinfo_a | getaddrinfo_a | libc.so.6 | GLIBC_2.2.5 | researched; netdb |
| GLIBC-getaliasbyname | getaliasbyname | libc.so.6 | — | not-started |
| GLIBC-getaliasbyname_r | getaliasbyname_r | libc.so.6 | — | not-started |
| GLIBC-getaliasent | getaliasent | libc.so.6 | — | not-started |
| GLIBC-getaliasent_r | getaliasent_r | libc.so.6 | — | not-started |
| GLIBC-getdate_err | getdate_err | libc.so.6 | — | documented |
| wave 7-c page (adjacent row absorbed): [getdate-getdate_r.md](glibc/misc/getdate-getdate_r.md) | 
| GLIBC-getdirentries | getdirentries | libc.so.6 | — | not-started |
| GLIBC-getdirentries64 | getdirentries64 | libc.so.6 | — | not-started |
| GLIBC-getdtablesize | getdtablesize | libc.so.6 | — | not-started |
| GLIBC-gethostent_r | gethostent_r | libc.so.6 | — | not-started |
| GLIBC-getifaddrs | getifaddrs | libc.so.6 | — | not-started |
| GLIBC-getipv4sourcefilter | getipv4sourcefilter | libc.so.6 | — | not-started |
| GLIBC-getlogin_r | getlogin_r | libc.so.6 | — | not-started |
| GLIBC-getmsg | getmsg | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-getnameinfo | getnameinfo | libc.so.6 | — | documented; Grouped |
| GLIBC-getnetbyaddr_r | getnetbyaddr_r | libc.so.6 | — | not-started |
| GLIBC-getnetbyname_r | getnetbyname_r | libc.so.6 | — | not-started |
| GLIBC-getnetent_r | getnetent_r | libc.so.6 | — | not-started |
| GLIBC-getnetname | getnetname | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-getpayloadf128 | getpayloadf128 | libm.so.6 | — | not-started |
| GLIBC-getpayloadf32 | getpayloadf32 | libm.so.6 | — | not-started |
| GLIBC-getpayloadf32x | getpayloadf32x | libm.so.6 | — | not-started |
| GLIBC-getpayloadf64 | getpayloadf64 | libm.so.6 | — | not-started |
| GLIBC-getpayloadf64x | getpayloadf64x | libm.so.6 | — | not-started |
| GLIBC-getpmsg | getpmsg | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-getprotobyname_r | getprotobyname_r | libc.so.6 | — | not-started |
| GLIBC-getprotobynumber_r | getprotobynumber_r | libc.so.6 | — | not-started |
| GLIBC-getprotoent_r | getprotoent_r | libc.so.6 | — | not-started |
| GLIBC-getpublickey | getpublickey | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-getpw | getpw | libc.so.6 | — | not-started |
| GLIBC-getresgid | getresgid | libc.so.6 | — | not-started |
| GLIBC-getresuid | getresuid | libc.so.6 | — | not-started |
| GLIBC-getrpcbyname | getrpcbyname | libc.so.6 | — | not-started |
| GLIBC-getrpcbyname_r | getrpcbyname_r | libc.so.6 | — | not-started |
| GLIBC-getrpcbynumber | getrpcbynumber | libc.so.6 | — | not-started |
| GLIBC-getrpcbynumber_r | getrpcbynumber_r | libc.so.6 | — | not-started |
| GLIBC-getrpcent | getrpcent | libc.so.6 | — | not-started |
| GLIBC-getrpcent_r | getrpcent_r | libc.so.6 | — | not-started |
| GLIBC-getrpcport | getrpcport | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-gets | gets | libc.so.6 | — | not-started |
| GLIBC-getsecretkey | getsecretkey | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-getservbyname_r | getservbyname_r | libc.so.6 | — | not-started |
| GLIBC-getservbyport_r | getservbyport_r | libc.so.6 | — | not-started |
| GLIBC-getservent_r | getservent_r | libc.so.6 | — | not-started |
| GLIBC-getsgent | getsgent | libc.so.6 | — | not-started |
| GLIBC-getsgent_r | getsgent_r | libc.so.6 | — | not-started |
| GLIBC-getsgnam | getsgnam | libc.so.6 | — | not-started |
| GLIBC-getsgnam_r | getsgnam_r | libc.so.6 | — | not-started |
| GLIBC-getsourcefilter | getsourcefilter | libc.so.6 | — | not-started |
| GLIBC-getspent | getspent | libc.so.6 | — | not-started |
| GLIBC-getspent_r | getspent_r | libc.so.6 | — | not-started |
| GLIBC-getspnam | getspnam | libc.so.6 | — | documented; Grouped |
| GLIBC-getspnam_r | getspnam_r | libc.so.6 | — | documented; Grouped |
| GLIBC-getttyent | getttyent | libc.so.6 | — | not-started |
| GLIBC-getttynam | getttynam | libc.so.6 | — | not-started |
| GLIBC-getusershell | getusershell | libc.so.6 | — | not-started |
| GLIBC-getwd | getwd | libc.so.6 | — | not-started |
| GLIBC-getxattr | getxattr | libc.so.6 | — | not-started |
| GLIBC-glob_pattern_p | glob_pattern_p | libc.so.6 | — | not-started |
| GLIBC-gnu_dev_major | gnu_dev_major | libc.so.6 | — | not-started |
| GLIBC-gnu_dev_makedev | gnu_dev_makedev | libc.so.6 | — | not-started |
| GLIBC-gnu_dev_minor | gnu_dev_minor | libc.so.6 | — | not-started |
| GLIBC-gnu_get_libc_release | gnu_get_libc_release | libc.so.6 | — | not-started |
| GLIBC-gnu_get_libc_version | gnu_get_libc_version | libc.so.6 | — | not-started |
| GLIBC-group_member | group_member | libc.so.6 | — | not-started |
| GLIBC-h_errlist | h_errlist | libc.so.6 | — | not-started |
| GLIBC-h_nerr | h_nerr | libc.so.6 | — | not-started |
| GLIBC-herror | herror | libc.so.6 | — | not-started |
| GLIBC-host2netname | host2netname | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-hstrerror | hstrerror | libc.so.6 | — | not-started |
| GLIBC-hypotf128 | hypotf128 | libm.so.6 | — | not-started |
| GLIBC-hypotf32 | hypotf32 | libm.so.6 | — | not-started |
| GLIBC-hypotf32x | hypotf32x | libm.so.6 | — | not-started |
| GLIBC-hypotf64 | hypotf64 | libm.so.6 | — | not-started |
| GLIBC-hypotf64x | hypotf64x | libm.so.6 | — | not-started |
| GLIBC-ilogbf128 | ilogbf128 | libm.so.6 | — | not-started |
| GLIBC-ilogbf32 | ilogbf32 | libm.so.6 | — | not-started |
| GLIBC-ilogbf32x | ilogbf32x | libm.so.6 | — | not-started |
| GLIBC-ilogbf64 | ilogbf64 | libm.so.6 | — | not-started |
| GLIBC-ilogbf64x | ilogbf64x | libm.so.6 | — | not-started |
| GLIBC-inet6_opt_append | inet6_opt_append | libc.so.6 | — | not-started |
| GLIBC-inet6_opt_find | inet6_opt_find | libc.so.6 | — | not-started |
| GLIBC-inet6_opt_finish | inet6_opt_finish | libc.so.6 | — | not-started |
| GLIBC-inet6_opt_get_val | inet6_opt_get_val | libc.so.6 | — | not-started |
| GLIBC-inet6_opt_init | inet6_opt_init | libc.so.6 | — | not-started |
| GLIBC-inet6_opt_next | inet6_opt_next | libc.so.6 | — | not-started |
| GLIBC-inet6_opt_set_val | inet6_opt_set_val | libc.so.6 | — | not-started |
| GLIBC-inet6_option_alloc | inet6_option_alloc | libc.so.6 | — | not-started |
| GLIBC-inet6_option_append | inet6_option_append | libc.so.6 | — | not-started |
| GLIBC-inet6_option_find | inet6_option_find | libc.so.6 | — | not-started |
| GLIBC-inet6_option_init | inet6_option_init | libc.so.6 | — | not-started |
| GLIBC-inet6_option_next | inet6_option_next | libc.so.6 | — | not-started |
| GLIBC-inet6_option_space | inet6_option_space | libc.so.6 | — | not-started |
| GLIBC-inet6_rth_add | inet6_rth_add | libc.so.6 | — | not-started |
| GLIBC-inet6_rth_getaddr | inet6_rth_getaddr | libc.so.6 | — | not-started |
| GLIBC-inet6_rth_init | inet6_rth_init | libc.so.6 | — | not-started |
| GLIBC-inet6_rth_reverse | inet6_rth_reverse | libc.so.6 | — | not-started |
| GLIBC-inet6_rth_segments | inet6_rth_segments | libc.so.6 | — | not-started |
| GLIBC-inet6_rth_space | inet6_rth_space | libc.so.6 | — | not-started |
| GLIBC-inet_net_ntop | inet_net_ntop | libresolv.so.2 | — | not-started |
| GLIBC-inet_net_pton | inet_net_pton | libresolv.so.2 | — | not-started |
| GLIBC-inet_neta | inet_neta | libresolv.so.2 | — | not-started |
| GLIBC-inet_nsap_addr | inet_nsap_addr | libc.so.6 | — | not-started |
| GLIBC-inet_nsap_ntoa | inet_nsap_ntoa | libc.so.6 | — | not-started |
| GLIBC-init_module | init_module | libc.so.6 | — | not-started |
| GLIBC-inotify_add_watch | inotify_add_watch | libc.so.6 | — | not-started |
| GLIBC-inotify_init | inotify_init | libc.so.6 | — | not-started |
| GLIBC-inotify_init1 | inotify_init1 | libc.so.6 | — | not-started |
| GLIBC-inotify_rm_watch | inotify_rm_watch | libc.so.6 | — | not-started |
| GLIBC-insque | insque | libc.so.6 | — | not-started |
| GLIBC-ioperm | ioperm | libc.so.6 | — | not-started |
| GLIBC-iopl | iopl | libc.so.6 | — | not-started |
| GLIBC-iruserok | iruserok | libc.so.6 | — | not-started |
| GLIBC-iruserok_af | iruserok_af | libc.so.6 | — | not-started |
| GLIBC-isalnum_l | isalnum_l | libc.so.6 | — | researched; ctype |
| GLIBC-isalpha_l | isalpha_l | libc.so.6 | — | researched; ctype |
| GLIBC-isastream | isastream | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-isblank_l | isblank_l | libc.so.6 | — | researched; ctype |
| GLIBC-iscntrl_l | iscntrl_l | libc.so.6 | — | researched; ctype |
| GLIBC-isctype | isctype | libc.so.6 | — | not-started |
| GLIBC-isdigit_l | isdigit_l | libc.so.6 | — | researched; ctype |
| GLIBC-isfdtype | isfdtype | libc.so.6 | — | not-started |
| GLIBC-isgraph_l | isgraph_l | libc.so.6 | — | researched; ctype |
| GLIBC-islower_l | islower_l | libc.so.6 | — | researched; ctype |
| GLIBC-isprint_l | isprint_l | libc.so.6 | — | researched; ctype |
| GLIBC-ispunct_l | ispunct_l | libc.so.6 | — | researched; ctype |
| GLIBC-isspace_l | isspace_l | libc.so.6 | — | researched; ctype |
| GLIBC-isupper_l | isupper_l | libc.so.6 | — | researched; ctype |
| GLIBC-iswalnum_l | iswalnum_l | libc.so.6 | — | researched; ctype |
| GLIBC-iswalpha_l | iswalpha_l | libc.so.6 | — | researched; ctype |
| GLIBC-iswblank_l | iswblank_l | libc.so.6 | — | researched; ctype |
| GLIBC-iswcntrl_l | iswcntrl_l | libc.so.6 | — | researched; ctype |
| GLIBC-iswctype_l | iswctype_l | libc.so.6 | — | researched; ctype |
| GLIBC-iswdigit_l | iswdigit_l | libc.so.6 | — | researched; ctype |
| GLIBC-iswgraph_l | iswgraph_l | libc.so.6 | — | researched; ctype |
| GLIBC-iswlower_l | iswlower_l | libc.so.6 | — | researched; ctype |
| GLIBC-iswprint_l | iswprint_l | libc.so.6 | — | researched; ctype |
| GLIBC-iswpunct_l | iswpunct_l | libc.so.6 | — | researched; ctype |
| GLIBC-iswspace_l | iswspace_l | libc.so.6 | — | researched; ctype |
| GLIBC-iswupper_l | iswupper_l | libc.so.6 | — | researched; ctype |
| GLIBC-iswxdigit_l | iswxdigit_l | libc.so.6 | — | researched; ctype |
| GLIBC-isxdigit_l | isxdigit_l | libc.so.6 | — | researched; ctype |
| GLIBC-j0f128 | j0f128 | libm.so.6 | — | not-started |
| GLIBC-j0f32 | j0f32 | libm.so.6 | — | not-started |
| GLIBC-j0f32x | j0f32x | libm.so.6 | — | not-started |
| GLIBC-j0f64 | j0f64 | libm.so.6 | — | not-started |
| GLIBC-j0f64x | j0f64x | libm.so.6 | — | not-started |
| GLIBC-j1f128 | j1f128 | libm.so.6 | — | not-started |
| GLIBC-j1f32 | j1f32 | libm.so.6 | — | not-started |
| GLIBC-j1f32x | j1f32x | libm.so.6 | — | not-started |
| GLIBC-j1f64 | j1f64 | libm.so.6 | — | not-started |
| GLIBC-j1f64x | j1f64x | libm.so.6 | — | not-started |
| GLIBC-jnf128 | jnf128 | libm.so.6 | — | not-started |
| GLIBC-jnf32 | jnf32 | libm.so.6 | — | not-started |
| GLIBC-jnf32x | jnf32x | libm.so.6 | — | not-started |
| GLIBC-jnf64 | jnf64 | libm.so.6 | — | not-started |
| GLIBC-jnf64x | jnf64x | libm.so.6 | — | not-started |
| GLIBC-key_decryptsession | key_decryptsession | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-key_decryptsession_pk | key_decryptsession_pk | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-key_encryptsession | key_encryptsession | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-key_encryptsession_pk | key_encryptsession_pk | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-key_gendes | key_gendes | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-key_get_conv | key_get_conv | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-key_secretkey_is_set | key_secretkey_is_set | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-key_setnet | key_setnet | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-key_setsecret | key_setsecret | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-klogctl | klogctl | libc.so.6 | — | not-started |
| GLIBC-lchmod | lchmod | libc.so.6 | — | not-started |
| GLIBC-lchown | lchown | libc.so.6 | — | documented; Grouped |
| GLIBC-lckpwdf | lckpwdf | libc.so.6 | — | not-started |
| GLIBC-ldexpf128 | ldexpf128 | libm.so.6 | — | not-started |
| GLIBC-ldexpf32 | ldexpf32 | libm.so.6 | — | not-started |
| GLIBC-ldexpf32x | ldexpf32x | libm.so.6 | — | not-started |
| GLIBC-ldexpf64 | ldexpf64 | libm.so.6 | — | not-started |
| GLIBC-ldexpf64x | ldexpf64x | libm.so.6 | — | not-started |
| GLIBC-lgammaf128 | lgammaf128 | libm.so.6 | — | not-started |
| GLIBC-lgammaf128_r | lgammaf128_r | libm.so.6 | — | not-started |
| GLIBC-lgammaf32 | lgammaf32 | libm.so.6 | — | not-started |
| GLIBC-lgammaf32_r | lgammaf32_r | libm.so.6 | — | not-started |
| GLIBC-lgammaf32x | lgammaf32x | libm.so.6 | — | not-started |
| GLIBC-lgammaf32x_r | lgammaf32x_r | libm.so.6 | — | not-started |
| GLIBC-lgammaf64 | lgammaf64 | libm.so.6 | — | not-started |
| GLIBC-lgammaf64_r | lgammaf64_r | libm.so.6 | — | not-started |
| GLIBC-lgammaf64x | lgammaf64x | libm.so.6 | — | not-started |
| GLIBC-lgammaf64x_r | lgammaf64x_r | libm.so.6 | — | not-started |
| GLIBC-lgetxattr | lgetxattr | libc.so.6 | — | not-started |
| GLIBC-listxattr | listxattr | libc.so.6 | — | not-started |
| GLIBC-llistxattr | llistxattr | libc.so.6 | — | not-started |
| GLIBC-llogbf128 | llogbf128 | libm.so.6 | — | not-started |
| GLIBC-llogbf32 | llogbf32 | libm.so.6 | — | not-started |
| GLIBC-llogbf32x | llogbf32x | libm.so.6 | — | not-started |
| GLIBC-llogbf64 | llogbf64 | libm.so.6 | — | not-started |
| GLIBC-llogbf64x | llogbf64x | libm.so.6 | — | not-started |
| GLIBC-llrintf128 | llrintf128 | libm.so.6 | — | not-started |
| GLIBC-llrintf32 | llrintf32 | libm.so.6 | — | not-started |
| GLIBC-llrintf32x | llrintf32x | libm.so.6 | — | not-started |
| GLIBC-llrintf64 | llrintf64 | libm.so.6 | — | not-started |
| GLIBC-llrintf64x | llrintf64x | libm.so.6 | — | not-started |
| GLIBC-llroundf128 | llroundf128 | libm.so.6 | — | not-started |
| GLIBC-llroundf32 | llroundf32 | libm.so.6 | — | not-started |
| GLIBC-llroundf32x | llroundf32x | libm.so.6 | — | not-started |
| GLIBC-llroundf64 | llroundf64 | libm.so.6 | — | not-started |
| GLIBC-llroundf64x | llroundf64x | libm.so.6 | — | not-started |
| GLIBC-llseek | llseek | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-loc1 | loc1 | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-loc2 | loc2 | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-lockf | lockf | libc.so.6 | — | not-started |
| GLIBC-lockf64 | lockf64 | libc.so.6 | — | not-started |
| GLIBC-locs | locs | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-log10f128 | log10f128 | libm.so.6 | — | not-started |
| GLIBC-log10f32 | log10f32 | libm.so.6 | — | not-started |
| GLIBC-log10f32x | log10f32x | libm.so.6 | — | not-started |
| GLIBC-log10f64 | log10f64 | libm.so.6 | — | not-started |
| GLIBC-log10f64x | log10f64x | libm.so.6 | — | not-started |
| GLIBC-log10p1f128 | log10p1f128 | libm.so.6 | — | not-started |
| GLIBC-log10p1f32 | log10p1f32 | libm.so.6 | — | not-started |
| GLIBC-log10p1f32x | log10p1f32x | libm.so.6 | — | not-started |
| GLIBC-log10p1f64 | log10p1f64 | libm.so.6 | — | not-started |
| GLIBC-log10p1f64x | log10p1f64x | libm.so.6 | — | not-started |
| GLIBC-log1pf128 | log1pf128 | libm.so.6 | — | not-started |
| GLIBC-log1pf32 | log1pf32 | libm.so.6 | — | not-started |
| GLIBC-log1pf32x | log1pf32x | libm.so.6 | — | not-started |
| GLIBC-log1pf64 | log1pf64 | libm.so.6 | — | not-started |
| GLIBC-log1pf64x | log1pf64x | libm.so.6 | — | not-started |
| GLIBC-log2f128 | log2f128 | libm.so.6 | — | not-started |
| GLIBC-log2f32 | log2f32 | libm.so.6 | — | not-started |
| GLIBC-log2f32x | log2f32x | libm.so.6 | — | not-started |
| GLIBC-log2f64 | log2f64 | libm.so.6 | — | not-started |
| GLIBC-log2f64x | log2f64x | libm.so.6 | — | not-started |
| GLIBC-log2p1f128 | log2p1f128 | libm.so.6 | — | not-started |
| GLIBC-log2p1f32 | log2p1f32 | libm.so.6 | — | not-started |
| GLIBC-log2p1f32x | log2p1f32x | libm.so.6 | — | not-started |
| GLIBC-log2p1f64 | log2p1f64 | libm.so.6 | — | not-started |
| GLIBC-log2p1f64x | log2p1f64x | libm.so.6 | — | not-started |
| GLIBC-logbf128 | logbf128 | libm.so.6 | — | not-started |
| GLIBC-logbf32 | logbf32 | libm.so.6 | — | not-started |
| GLIBC-logbf32x | logbf32x | libm.so.6 | — | not-started |
| GLIBC-logbf64 | logbf64 | libm.so.6 | — | not-started |
| GLIBC-logbf64x | logbf64x | libm.so.6 | — | not-started |
| GLIBC-logf128 | logf128 | libm.so.6 | — | not-started |
| GLIBC-logf32 | logf32 | libm.so.6 | — | not-started |
| GLIBC-logf32x | logf32x | libm.so.6 | — | not-started |
| GLIBC-logf64 | logf64 | libm.so.6 | — | not-started |
| GLIBC-logf64x | logf64x | libm.so.6 | — | not-started |
| GLIBC-logp1f128 | logp1f128 | libm.so.6 | — | not-started |
| GLIBC-logp1f32 | logp1f32 | libm.so.6 | — | not-started |
| GLIBC-logp1f32x | logp1f32x | libm.so.6 | — | not-started |
| GLIBC-logp1f64 | logp1f64 | libm.so.6 | — | not-started |
| GLIBC-logp1f64x | logp1f64x | libm.so.6 | — | not-started |
| GLIBC-lremovexattr | lremovexattr | libc.so.6 | — | not-started |
| GLIBC-lrintf128 | lrintf128 | libm.so.6 | — | not-started |
| GLIBC-lrintf32 | lrintf32 | libm.so.6 | — | not-started |
| GLIBC-lrintf32x | lrintf32x | libm.so.6 | — | not-started |
| GLIBC-lrintf64 | lrintf64 | libm.so.6 | — | not-started |
| GLIBC-lrintf64x | lrintf64x | libm.so.6 | — | not-started |
| GLIBC-lroundf128 | lroundf128 | libm.so.6 | — | not-started |
| GLIBC-lroundf32 | lroundf32 | libm.so.6 | — | not-started |
| GLIBC-lroundf32x | lroundf32x | libm.so.6 | — | not-started |
| GLIBC-lroundf64 | lroundf64 | libm.so.6 | — | not-started |
| GLIBC-lroundf64x | lroundf64x | libm.so.6 | — | not-started |
| GLIBC-lsetxattr | lsetxattr | libc.so.6 | — | not-started |
| GLIBC-mallinfo | mallinfo | libc.so.6 | — | documented; grouped |
| GLIBC-malloc_info | malloc_info | libc.so.6 | — | researched; allocation |
| GLIBC-malloc_stats | malloc_stats | libc.so.6 | — | researched; allocation |
| GLIBC-malloc_trim | malloc_trim | libc.so.6 | — | researched; allocation |
| GLIBC-malloc_usable_size | malloc_usable_size | libc.so.6 | — | documented; full |
| GLIBC-mallwatch | mallwatch | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-matherr | matherr | libm.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-mbrtoc16 | mbrtoc16 | libc.so.6 | — | not-started |
| GLIBC-mbrtoc32 | mbrtoc32 | libc.so.6 | — | not-started |
| GLIBC-mbrtoc8 | mbrtoc8 | libc.so.6 | — | not-started |
| GLIBC-mcheck_check_all | mcheck_check_all | libc.so.6 | — | not-started |
| GLIBC-mcheck_pedantic | mcheck_pedantic | libc.so.6 | — | not-started |
| GLIBC-mcount | mcount | libc.so.6 | — | not-started |
| GLIBC-mincore | mincore | libc.so.6 | — | not-started |
| GLIBC-mkfifoat | mkfifoat | libc.so.6 | — | not-started |
| GLIBC-mknodat | mknodat | libc.so.6 | — | not-started |
| GLIBC-mkostemp | mkostemp | libc.so.6 | — | not-started |
| GLIBC-mkostemp64 | mkostemp64 | libc.so.6 | — | not-started |
| GLIBC-mkostemps | mkostemps | libc.so.6 | — | not-started |
| GLIBC-mkostemps64 | mkostemps64 | libc.so.6 | — | not-started |
| GLIBC-mkstemp64 | mkstemp64 | libc.so.6 | — | not-started |
| GLIBC-mkstemps | mkstemps | libc.so.6 | — | not-started |
| GLIBC-mkstemps64 | mkstemps64 | libc.so.6 | — | not-started |
| GLIBC-modff128 | modff128 | libm.so.6 | — | not-started |
| GLIBC-modff32 | modff32 | libm.so.6 | — | not-started |
| GLIBC-modff32x | modff32x | libm.so.6 | — | not-started |
| GLIBC-modff64 | modff64 | libm.so.6 | — | not-started |
| GLIBC-modff64x | modff64x | libm.so.6 | — | not-started |
| GLIBC-modify_ldt | modify_ldt | libc.so.6 | — | not-started |
| GLIBC-moncontrol | moncontrol | libc.so.6 | — | not-started |
| GLIBC-monstartup | monstartup | libc.so.6 | — | not-started |
| GLIBC-mount_setattr | mount_setattr | libc.so.6 | — | not-started |
| GLIBC-move_mount | move_mount | libc.so.6 | — | not-started |
| GLIBC-mq_close | mq_close | libc.so.6 | GLIBC_2.3.4 | not-started |
| GLIBC-mq_getattr | mq_getattr | libc.so.6 | GLIBC_2.3.4 | not-started |
| GLIBC-mq_notify | mq_notify | libc.so.6 | GLIBC_2.3.4 | not-started |
| GLIBC-mq_open | mq_open | libc.so.6 | GLIBC_2.3.4 | not-started |
| GLIBC-mq_receive | mq_receive | libc.so.6 | GLIBC_2.3.4 | not-started |
| GLIBC-mq_send | mq_send | libc.so.6 | GLIBC_2.3.4 | not-started |
| GLIBC-mq_setattr | mq_setattr | libc.so.6 | GLIBC_2.3.4 | not-started |
| GLIBC-mq_timedreceive | mq_timedreceive | libc.so.6 | GLIBC_2.3.4 | not-started |
| GLIBC-mq_timedsend | mq_timedsend | libc.so.6 | GLIBC_2.3.4 | not-started |
| GLIBC-mq_unlink | mq_unlink | libc.so.6 | GLIBC_2.3.4 | not-started |
| GLIBC-msgctl | msgctl | libc.so.6 | — | not-started |
| GLIBC-msgget | msgget | libc.so.6 | — | not-started |
| GLIBC-msgrcv | msgrcv | libc.so.6 | — | not-started |
| GLIBC-msgsnd | msgsnd | libc.so.6 | — | not-started |
| GLIBC-name_to_handle_at | name_to_handle_at | libc.so.6 | — | not-started |
| GLIBC-nanf128 | nanf128 | libm.so.6 | — | not-started |
| GLIBC-nanf32 | nanf32 | libm.so.6 | — | not-started |
| GLIBC-nanf32x | nanf32x | libm.so.6 | — | not-started |
| GLIBC-nanf64 | nanf64 | libm.so.6 | — | not-started |
| GLIBC-nanf64x | nanf64x | libm.so.6 | — | not-started |
| GLIBC-nearbyintf128 | nearbyintf128 | libm.so.6 | — | not-started |
| GLIBC-nearbyintf32 | nearbyintf32 | libm.so.6 | — | not-started |
| GLIBC-nearbyintf32x | nearbyintf32x | libm.so.6 | — | not-started |
| GLIBC-nearbyintf64 | nearbyintf64 | libm.so.6 | — | not-started |
| GLIBC-nearbyintf64x | nearbyintf64x | libm.so.6 | — | not-started |
| GLIBC-netname2host | netname2host | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-netname2user | netname2user | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-newlocale | newlocale | libc.so.6 | — | documented; Grouped |
| GLIBC-nextafterf128 | nextafterf128 | libm.so.6 | — | not-started |
| GLIBC-nextafterf32 | nextafterf32 | libm.so.6 | — | not-started |
| GLIBC-nextafterf32x | nextafterf32x | libm.so.6 | — | not-started |
| GLIBC-nextafterf64 | nextafterf64 | libm.so.6 | — | not-started |
| GLIBC-nextafterf64x | nextafterf64x | libm.so.6 | — | not-started |
| GLIBC-nextdownf128 | nextdownf128 | libm.so.6 | — | not-started |
| GLIBC-nextdownf32 | nextdownf32 | libm.so.6 | — | not-started |
| GLIBC-nextdownf32x | nextdownf32x | libm.so.6 | — | not-started |
| GLIBC-nextdownf64 | nextdownf64 | libm.so.6 | — | not-started |
| GLIBC-nextdownf64x | nextdownf64x | libm.so.6 | — | not-started |
| GLIBC-nextupf128 | nextupf128 | libm.so.6 | — | not-started |
| GLIBC-nextupf32 | nextupf32 | libm.so.6 | — | not-started |
| GLIBC-nextupf32x | nextupf32x | libm.so.6 | — | not-started |
| GLIBC-nextupf64 | nextupf64 | libm.so.6 | — | not-started |
| GLIBC-nextupf64x | nextupf64x | libm.so.6 | — | not-started |
| GLIBC-nfsservctl | nfsservctl | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-nis_add | nis_add | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-nis_add_entry | nis_add_entry | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-nis_addmember | nis_addmember | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-nis_checkpoint | nis_checkpoint | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-nis_clone_directory | nis_clone_directory | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-nis_clone_object | nis_clone_object | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-nis_clone_result | nis_clone_result | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-nis_creategroup | nis_creategroup | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-nis_destroy_object | nis_destroy_object | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-nis_destroygroup | nis_destroygroup | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-nis_dir_cmp | nis_dir_cmp | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-nis_domain_of | nis_domain_of | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-nis_domain_of_r | nis_domain_of_r | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-nis_first_entry | nis_first_entry | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-nis_free_directory | nis_free_directory | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-nis_free_object | nis_free_object | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-nis_free_request | nis_free_request | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-nis_freenames | nis_freenames | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-nis_freeresult | nis_freeresult | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-nis_freeservlist | nis_freeservlist | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-nis_freetags | nis_freetags | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-nis_getnames | nis_getnames | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-nis_getservlist | nis_getservlist | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-nis_ismember | nis_ismember | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-nis_leaf_of | nis_leaf_of | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-nis_leaf_of_r | nis_leaf_of_r | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-nis_lerror | nis_lerror | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-nis_list | nis_list | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-nis_local_directory | nis_local_directory | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-nis_local_group | nis_local_group | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-nis_local_host | nis_local_host | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-nis_local_principal | nis_local_principal | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-nis_lookup | nis_lookup | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-nis_mkdir | nis_mkdir | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-nis_modify | nis_modify | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-nis_modify_entry | nis_modify_entry | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-nis_name_of | nis_name_of | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-nis_name_of_r | nis_name_of_r | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-nis_next_entry | nis_next_entry | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-nis_perror | nis_perror | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-nis_ping | nis_ping | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-nis_print_directory | nis_print_directory | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-nis_print_entry | nis_print_entry | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-nis_print_group | nis_print_group | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-nis_print_group_entry | nis_print_group_entry | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-nis_print_link | nis_print_link | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-nis_print_object | nis_print_object | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-nis_print_result | nis_print_result | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-nis_print_rights | nis_print_rights | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-nis_print_table | nis_print_table | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-nis_read_obj | nis_read_obj | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-nis_remove | nis_remove | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-nis_remove_entry | nis_remove_entry | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-nis_removemember | nis_removemember | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-nis_rmdir | nis_rmdir | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-nis_servstate | nis_servstate | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-nis_sperrno | nis_sperrno | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-nis_sperror | nis_sperror | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-nis_sperror_r | nis_sperror_r | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-nis_stats | nis_stats | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-nis_verifygroup | nis_verifygroup | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-nis_write_obj | nis_write_obj | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-nl_langinfo_l | nl_langinfo_l | libc.so.6 | — | documented |
| wave 7-c page (adjacent row absorbed): [nl_langinfo.md](glibc/fs/nl_langinfo.md) | 
| GLIBC-ns_datetosecs | ns_datetosecs | libresolv.so.2 | — | not-started |
| GLIBC-ns_format_ttl | ns_format_ttl | libresolv.so.2 | — | not-started |
| GLIBC-ns_get16 | ns_get16 | libresolv.so.2 | — | not-started |
| GLIBC-ns_get32 | ns_get32 | libresolv.so.2 | — | not-started |
| GLIBC-ns_initparse | ns_initparse | libresolv.so.2 | — | not-started |
| GLIBC-ns_makecanon | ns_makecanon | libresolv.so.2 | — | not-started |
| GLIBC-ns_msg_getflag | ns_msg_getflag | libresolv.so.2 | — | not-started |
| GLIBC-ns_name_compress | ns_name_compress | libc.so.6 | GLIBC_2.9 | not-started |
| GLIBC-ns_name_ntol | ns_name_ntol | libresolv.so.2 | — | not-started |
| GLIBC-ns_name_ntop | ns_name_ntop | libc.so.6 | GLIBC_2.9 | not-started |
| GLIBC-ns_name_pack | ns_name_pack | libc.so.6 | GLIBC_2.9 | not-started |
| GLIBC-ns_name_pton | ns_name_pton | libc.so.6 | GLIBC_2.9 | not-started |
| GLIBC-ns_name_rollback | ns_name_rollback | libresolv.so.2 | — | not-started |
| GLIBC-ns_name_skip | ns_name_skip | libc.so.6 | GLIBC_2.9 | not-started |
| GLIBC-ns_name_uncompress | ns_name_uncompress | libc.so.6 | GLIBC_2.9 | not-started |
| GLIBC-ns_name_unpack | ns_name_unpack | libc.so.6 | GLIBC_2.9 | not-started |
| GLIBC-ns_parse_ttl | ns_parse_ttl | libresolv.so.2 | — | not-started |
| GLIBC-ns_parserr | ns_parserr | libresolv.so.2 | — | not-started |
| GLIBC-ns_put16 | ns_put16 | libresolv.so.2 | — | not-started |
| GLIBC-ns_put32 | ns_put32 | libresolv.so.2 | — | not-started |
| GLIBC-ns_samedomain | ns_samedomain | libresolv.so.2 | — | not-started |
| GLIBC-ns_samename | ns_samename | libresolv.so.2 | — | not-started |
| GLIBC-ns_skiprr | ns_skiprr | libresolv.so.2 | — | not-started |
| GLIBC-ns_sprintrr | ns_sprintrr | libresolv.so.2 | — | not-started |
| GLIBC-ns_sprintrrf | ns_sprintrrf | libresolv.so.2 | — | not-started |
| GLIBC-ns_subdomain | ns_subdomain | libresolv.so.2 | — | not-started |
| GLIBC-ntp_gettimex | ntp_gettimex | libc.so.6 | — | not-started |
| GLIBC-obstack_alloc_failed_handler | obstack_alloc_failed_handler | libc.so.6 | — | not-started |
| GLIBC-obstack_exit_failure | obstack_exit_failure | libc.so.6 | — | not-started |
| GLIBC-open_by_handle_at | open_by_handle_at | libc.so.6 | — | not-started |
| GLIBC-open_tree | open_tree | libc.so.6 | — | not-started |
| GLIBC-open_wmemstream | open_wmemstream | libc.so.6 | — | not-started |
| GLIBC-optarg | optarg | libc.so.6 | — | not-started |
| GLIBC-opterr | opterr | libc.so.6 | — | not-started |
| GLIBC-optind | optind | libc.so.6 | — | not-started |
| GLIBC-optopt | optopt | libc.so.6 | — | not-started |
| GLIBC-passwd2des | passwd2des | libc.so.6 | GLIBC_2.2.5 | researched; crypt |
| GLIBC-personality | personality | libc.so.6 | — | not-started |
| GLIBC-pidfd_getfd | pidfd_getfd | libc.so.6 | — | not-started |
| GLIBC-pidfd_open | pidfd_open | libc.so.6 | — | not-started |
| GLIBC-pidfd_send_signal | pidfd_send_signal | libc.so.6 | — | not-started |
| GLIBC-pidfd_spawn | pidfd_spawn | libc.so.6 | — | not-started |
| GLIBC-pidfd_spawnp | pidfd_spawnp | libc.so.6 | — | not-started |
| GLIBC-pipe2 | pipe2 | libc.so.6 | — | documented; pipe/pipe2 |
| GLIBC-pivot_root | pivot_root | libc.so.6 | — | not-started |
| GLIBC-pmap_getmaps | pmap_getmaps | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-pmap_getport | pmap_getport | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-pmap_rmtcall | pmap_rmtcall | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-pmap_set | pmap_set | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-pmap_unset | pmap_unset | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-posix_fadvise | posix_fadvise | libc.so.6 | — | not-started |
| GLIBC-posix_fadvise64 | posix_fadvise64 | libc.so.6 | — | not-started |
| GLIBC-posix_madvise | posix_madvise | libc.so.6 | — | not-started |
| GLIBC-posix_spawn | posix_spawn | libc.so.6 | GLIBC_2.2.5 | documented; full |
| GLIBC-posix_spawn_file_actions_addchdir_np | posix_spawn_file_actions_addchdir_np | libc.so.6 | — | documented; grouped |
| GLIBC-posix_spawn_file_actions_addclose | posix_spawn_file_actions_addclose | libc.so.6 | — | documented; grouped |
| GLIBC-posix_spawn_file_actions_addclosefrom_np | posix_spawn_file_actions_addclosefrom_np | libc.so.6 | — | documented; grouped |
| GLIBC-posix_spawn_file_actions_adddup2 | posix_spawn_file_actions_adddup2 | libc.so.6 | — | documented; grouped |
| GLIBC-posix_spawn_file_actions_addfchdir_np | posix_spawn_file_actions_addfchdir_np | libc.so.6 | — | documented; grouped |
| GLIBC-posix_spawn_file_actions_addopen | posix_spawn_file_actions_addopen | libc.so.6 | — | documented; grouped |
| GLIBC-posix_spawn_file_actions_addtcsetpgrp_np | posix_spawn_file_actions_addtcsetpgrp_np | libc.so.6 | — | documented; grouped |
| GLIBC-posix_spawn_file_actions_destroy | posix_spawn_file_actions_destroy | libc.so.6 | — | documented; grouped |
| GLIBC-posix_spawn_file_actions_init | posix_spawn_file_actions_init | libc.so.6 | — | documented; grouped |
| GLIBC-posix_spawnattr_destroy | posix_spawnattr_destroy | libc.so.6 | — | documented; grouped |
| GLIBC-posix_spawnattr_getcgroup_np | posix_spawnattr_getcgroup_np | libc.so.6 | — | documented; grouped |
| GLIBC-posix_spawnattr_getflags | posix_spawnattr_getflags | libc.so.6 | — | documented; grouped |
| GLIBC-posix_spawnattr_getpgroup | posix_spawnattr_getpgroup | libc.so.6 | — | documented; grouped |
| GLIBC-posix_spawnattr_getschedparam | posix_spawnattr_getschedparam | libc.so.6 | — | documented; grouped |
| GLIBC-posix_spawnattr_getschedpolicy | posix_spawnattr_getschedpolicy | libc.so.6 | — | documented; grouped |
| GLIBC-posix_spawnattr_getsigdefault | posix_spawnattr_getsigdefault | libc.so.6 | — | documented; grouped |
| GLIBC-posix_spawnattr_getsigmask | posix_spawnattr_getsigmask | libc.so.6 | — | documented; grouped |
| GLIBC-posix_spawnattr_init | posix_spawnattr_init | libc.so.6 | — | documented; grouped |
| GLIBC-posix_spawnattr_setcgroup_np | posix_spawnattr_setcgroup_np | libc.so.6 | — | documented; grouped |
| GLIBC-posix_spawnattr_setflags | posix_spawnattr_setflags | libc.so.6 | — | documented; grouped |
| GLIBC-posix_spawnattr_setpgroup | posix_spawnattr_setpgroup | libc.so.6 | — | documented; grouped |
| GLIBC-posix_spawnattr_setschedparam | posix_spawnattr_setschedparam | libc.so.6 | — | documented; grouped |
| GLIBC-posix_spawnattr_setschedpolicy | posix_spawnattr_setschedpolicy | libc.so.6 | — | documented; grouped |
| GLIBC-posix_spawnattr_setsigdefault | posix_spawnattr_setsigdefault | libc.so.6 | — | documented; grouped |
| GLIBC-posix_spawnattr_setsigmask | posix_spawnattr_setsigmask | libc.so.6 | — | documented; grouped |
| GLIBC-posix_spawnp | posix_spawnp | libc.so.6 | GLIBC_2.2.5 | documented; grouped |
| GLIBC-pow10 | pow10 | libm.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-pow10f | pow10f | libm.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-pow10l | pow10l | libm.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-powf128 | powf128 | libm.so.6 | — | not-started |
| GLIBC-powf32 | powf32 | libm.so.6 | — | not-started |
| GLIBC-powf32x | powf32x | libm.so.6 | — | not-started |
| GLIBC-powf64 | powf64 | libm.so.6 | — | not-started |
| GLIBC-powf64x | powf64x | libm.so.6 | — | not-started |
| GLIBC-ppoll | ppoll | libc.so.6 | — | not-started |
| GLIBC-prctl | prctl | libc.so.6 | — | not-started |
| GLIBC-prlimit | prlimit | libc.so.6 | — | not-started |
| GLIBC-prlimit64 | prlimit64 | libc.so.6 | — | not-started |
| GLIBC-process_madvise | process_madvise | libc.so.6 | — | not-started |
| GLIBC-process_mrelease | process_mrelease | libc.so.6 | — | not-started |
| GLIBC-process_vm_readv | process_vm_readv | libc.so.6 | — | not-started |
| GLIBC-process_vm_writev | process_vm_writev | libc.so.6 | — | not-started |
| GLIBC-profil | profil | libc.so.6 | — | not-started |
| GLIBC-pselect | pselect | libc.so.6 | — | not-started |
| GLIBC-psiginfo | psiginfo | libc.so.6 | — | not-started |
| GLIBC-pthread_atfork | pthread_atfork | libc.so.6 | GLIBC_2.2.5 | documented; full |
| GLIBC-pthread_attr_getguardsize | pthread_attr_getguardsize | libc.so.6 | GLIBC_2.2.5 | researched; attr |
| GLIBC-pthread_attr_getinheritsched | pthread_attr_getinheritsched | libc.so.6 | — | researched; attr |
| GLIBC-pthread_attr_getschedparam | pthread_attr_getschedparam | libc.so.6 | — | researched; attr |
| GLIBC-pthread_attr_getschedpolicy | pthread_attr_getschedpolicy | libc.so.6 | — | researched; attr |
| GLIBC-pthread_attr_getscope | pthread_attr_getscope | libc.so.6 | — | researched; attr |
| GLIBC-pthread_attr_getstack | pthread_attr_getstack | libc.so.6 | GLIBC_2.2.5 | researched; attr |
| GLIBC-pthread_attr_getstackaddr | pthread_attr_getstackaddr | libc.so.6 | GLIBC_2.2.5 | researched; attr |
| GLIBC-pthread_attr_getstacksize | pthread_attr_getstacksize | libc.so.6 | GLIBC_2.2.5 | researched; attr |
| GLIBC-pthread_attr_setguardsize | pthread_attr_setguardsize | libc.so.6 | GLIBC_2.2.5 | researched; attr |
| GLIBC-pthread_attr_setinheritsched | pthread_attr_setinheritsched | libc.so.6 | — | researched; attr |
| GLIBC-pthread_attr_setschedparam | pthread_attr_setschedparam | libc.so.6 | — | researched; attr |
| GLIBC-pthread_attr_setschedpolicy | pthread_attr_setschedpolicy | libc.so.6 | — | researched; attr |
| GLIBC-pthread_attr_setscope | pthread_attr_setscope | libc.so.6 | — | researched; attr |
| GLIBC-pthread_attr_setstack | pthread_attr_setstack | libc.so.6 | GLIBC_2.2.5 | researched; attr |
| GLIBC-pthread_attr_setstackaddr | pthread_attr_setstackaddr | libc.so.6 | GLIBC_2.2.5 | researched; attr |
| GLIBC-pthread_attr_setstacksize | pthread_attr_setstacksize | libc.so.6 | GLIBC_2.2.5 | researched; attr |
| GLIBC-pthread_barrierattr_destroy | pthread_barrierattr_destroy | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-pthread_barrierattr_getpshared | pthread_barrierattr_getpshared | libc.so.6 | GLIBC_2.3.3 | not-started |
| GLIBC-pthread_barrierattr_init | pthread_barrierattr_init | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-pthread_barrierattr_setpshared | pthread_barrierattr_setpshared | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-pthread_cancel | pthread_cancel | libc.so.6 | GLIBC_2.2.5 | documented; full |
| GLIBC-pthread_cond_broadcast | pthread_cond_broadcast | libc.so.6 | GLIBC_2.2.5 | documented; grouped |
| GLIBC-pthread_cond_destroy | pthread_cond_destroy | libc.so.6 | GLIBC_2.2.5 | documented; grouped |
| GLIBC-pthread_cond_init | pthread_cond_init | libc.so.6 | GLIBC_2.2.5 | documented; grouped |
| GLIBC-pthread_cond_signal | pthread_cond_signal | libc.so.6 | GLIBC_2.2.5 | documented; grouped |
| GLIBC-pthread_cond_timedwait | pthread_cond_timedwait | libc.so.6 | GLIBC_2.2.5 | documented; grouped |
| GLIBC-pthread_cond_wait | pthread_cond_wait | libc.so.6 | GLIBC_2.2.5 | documented; grouped |
| GLIBC-pthread_condattr_destroy | pthread_condattr_destroy | libc.so.6 | — | researched; cond |
| GLIBC-pthread_condattr_getclock | pthread_condattr_getclock | libc.so.6 | GLIBC_2.3.3 | researched; cond |
| GLIBC-pthread_condattr_getpshared | pthread_condattr_getpshared | libc.so.6 | GLIBC_2.2.5 | researched; cond |
| GLIBC-pthread_condattr_init | pthread_condattr_init | libc.so.6 | — | researched; cond |
| GLIBC-pthread_condattr_setclock | pthread_condattr_setclock | libc.so.6 | GLIBC_2.3.3 | researched; cond |
| GLIBC-pthread_condattr_setpshared | pthread_condattr_setpshared | libc.so.6 | GLIBC_2.2.5 | researched; cond |
| GLIBC-pthread_exit | pthread_exit | libc.so.6 | — | not-started |
| GLIBC-pthread_getattr_np | pthread_getattr_np | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-pthread_getconcurrency | pthread_getconcurrency | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-pthread_getschedparam | pthread_getschedparam | libc.so.6 | — | not-started |
| GLIBC-pthread_kill_other_threads_np | pthread_kill_other_threads_np | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-pthread_mutex_consistent | pthread_mutex_consistent | libc.so.6 | GLIBC_2.12 | not-started |
| GLIBC-pthread_mutex_consistent_np | pthread_mutex_consistent_np | libc.so.6 | GLIBC_2.4 | not-started |
| GLIBC-pthread_mutex_getprioceiling | pthread_mutex_getprioceiling | libc.so.6 | GLIBC_2.4 | not-started |
| GLIBC-pthread_mutex_setprioceiling | pthread_mutex_setprioceiling | libc.so.6 | GLIBC_2.4 | not-started |
| GLIBC-pthread_mutexattr_getkind_np | pthread_mutexattr_getkind_np | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-pthread_mutexattr_getprioceiling | pthread_mutexattr_getprioceiling | libc.so.6 | GLIBC_2.4 | not-started |
| GLIBC-pthread_mutexattr_getprotocol | pthread_mutexattr_getprotocol | libc.so.6 | GLIBC_2.4 | not-started |
| GLIBC-pthread_mutexattr_getpshared | pthread_mutexattr_getpshared | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-pthread_mutexattr_getrobust | pthread_mutexattr_getrobust | libc.so.6 | GLIBC_2.12 | not-started |
| GLIBC-pthread_mutexattr_getrobust_np | pthread_mutexattr_getrobust_np | libc.so.6 | GLIBC_2.4 | not-started |
| GLIBC-pthread_mutexattr_setkind_np | pthread_mutexattr_setkind_np | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-pthread_mutexattr_setprioceiling | pthread_mutexattr_setprioceiling | libc.so.6 | GLIBC_2.4 | not-started |
| GLIBC-pthread_mutexattr_setprotocol | pthread_mutexattr_setprotocol | libc.so.6 | GLIBC_2.4 | not-started |
| GLIBC-pthread_mutexattr_setpshared | pthread_mutexattr_setpshared | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-pthread_mutexattr_setrobust | pthread_mutexattr_setrobust | libc.so.6 | GLIBC_2.12 | not-started |
| GLIBC-pthread_mutexattr_setrobust_np | pthread_mutexattr_setrobust_np | libc.so.6 | GLIBC_2.4 | not-started |
| GLIBC-pthread_rwlock_destroy | pthread_rwlock_destroy | libc.so.6 | GLIBC_2.2.5 | researched; rwlock |
| GLIBC-pthread_rwlock_init | pthread_rwlock_init | libc.so.6 | GLIBC_2.2.5 | researched; rwlock |
| GLIBC-pthread_rwlock_rdlock | pthread_rwlock_rdlock | libc.so.6 | GLIBC_2.2.5 | researched; rwlock |
| GLIBC-pthread_rwlock_timedrdlock | pthread_rwlock_timedrdlock | libc.so.6 | GLIBC_2.2.5 | researched; rwlock |
| GLIBC-pthread_rwlock_timedwrlock | pthread_rwlock_timedwrlock | libc.so.6 | GLIBC_2.2.5 | researched; rwlock |
| GLIBC-pthread_rwlock_tryrdlock | pthread_rwlock_tryrdlock | libc.so.6 | GLIBC_2.2.5 | researched; rwlock |
| GLIBC-pthread_rwlock_trywrlock | pthread_rwlock_trywrlock | libc.so.6 | GLIBC_2.2.5 | researched; rwlock |
| GLIBC-pthread_rwlock_unlock | pthread_rwlock_unlock | libc.so.6 | GLIBC_2.2.5 | researched; rwlock |
| GLIBC-pthread_rwlock_wrlock | pthread_rwlock_wrlock | libc.so.6 | GLIBC_2.2.5 | researched; rwlock |
| GLIBC-pthread_rwlockattr_destroy | pthread_rwlockattr_destroy | libc.so.6 | GLIBC_2.2.5 | researched; rwlock |
| GLIBC-pthread_rwlockattr_getkind_np | pthread_rwlockattr_getkind_np | libc.so.6 | GLIBC_2.2.5 | researched; rwlock |
| GLIBC-pthread_rwlockattr_getpshared | pthread_rwlockattr_getpshared | libc.so.6 | GLIBC_2.2.5 | researched; rwlock |
| GLIBC-pthread_rwlockattr_init | pthread_rwlockattr_init | libc.so.6 | GLIBC_2.2.5 | researched; rwlock |
| GLIBC-pthread_rwlockattr_setkind_np | pthread_rwlockattr_setkind_np | libc.so.6 | GLIBC_2.2.5 | researched; rwlock |
| GLIBC-pthread_rwlockattr_setpshared | pthread_rwlockattr_setpshared | libc.so.6 | GLIBC_2.2.5 | researched; rwlock |
| GLIBC-pthread_setcancelstate | pthread_setcancelstate | libc.so.6 | — | documented; grouped |
| GLIBC-pthread_setcanceltype | pthread_setcanceltype | libc.so.6 | — | documented; grouped |
| GLIBC-pthread_setconcurrency | pthread_setconcurrency | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-pthread_setschedparam | pthread_setschedparam | libc.so.6 | — | not-started |
| GLIBC-pthread_setschedprio | pthread_setschedprio | libc.so.6 | GLIBC_2.3.4 | not-started |
| GLIBC-pthread_sigqueue | pthread_sigqueue | libc.so.6 | GLIBC_2.11 | not-started |
| GLIBC-pthread_testcancel | pthread_testcancel | libc.so.6 | GLIBC_2.2.5 | documented; grouped |
| GLIBC-pthread_yield | pthread_yield | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-ptrace | ptrace | libc.so.6 | — | not-started |
| GLIBC-putgrent | putgrent | libc.so.6 | — | not-started |
| GLIBC-putmsg | putmsg | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-putpmsg | putpmsg | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-putsgent | putsgent | libc.so.6 | — | not-started |
| GLIBC-putspent | putspent | libc.so.6 | — | not-started |
| GLIBC-pvalloc | pvalloc | libc.so.6 | — | researched; allocation |
| GLIBC-qsort_r | qsort_r | libc.so.6 | — | documented; grouped |
| GLIBC-query_module | query_module | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-quick_exit | quick_exit | libc.so.6 | GLIBC_2.10 | not-started |
| GLIBC-quotactl | quotactl | libc.so.6 | — | not-started |
| GLIBC-rcmd | rcmd | libc.so.6 | — | not-started |
| GLIBC-rcmd_af | rcmd_af | libc.so.6 | — | not-started |
| GLIBC-re_comp | re_comp | libc.so.6 | — | not-started |
| GLIBC-re_compile_fastmap | re_compile_fastmap | libc.so.6 | — | not-started |
| GLIBC-re_compile_pattern | re_compile_pattern | libc.so.6 | — | not-started |
| GLIBC-re_exec | re_exec | libc.so.6 | — | not-started |
| GLIBC-re_match | re_match | libc.so.6 | — | not-started |
| GLIBC-re_match_2 | re_match_2 | libc.so.6 | — | not-started |
| GLIBC-re_max_failures | re_max_failures | libc.so.6 | — | not-started |
| GLIBC-re_search | re_search | libc.so.6 | — | not-started |
| GLIBC-re_search_2 | re_search_2 | libc.so.6 | — | not-started |
| GLIBC-re_set_registers | re_set_registers | libc.so.6 | — | not-started |
| GLIBC-re_set_syntax | re_set_syntax | libc.so.6 | — | not-started |
| GLIBC-re_syntax_options | re_syntax_options | libc.so.6 | — | not-started |
| GLIBC-readahead | readahead | libc.so.6 | — | not-started |
| GLIBC-readColdStartFile | readColdStartFile | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-readlinkat | readlinkat | libc.so.6 | — | not-started |
| GLIBC-reboot | reboot | libc.so.6 | — | researched; reboot |
| GLIBC-recvmmsg | recvmmsg | libc.so.6 | — | researched; netdb |
| GLIBC-register_printf_modifier | register_printf_modifier | libc.so.6 | — | not-started |
| GLIBC-register_printf_specifier | register_printf_specifier | libc.so.6 | — | not-started |
| GLIBC-register_printf_type | register_printf_type | libc.so.6 | — | not-started |
| GLIBC-registerrpc | registerrpc | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-remainderf128 | remainderf128 | libm.so.6 | — | not-started |
| GLIBC-remainderf32 | remainderf32 | libm.so.6 | — | not-started |
| GLIBC-remainderf32x | remainderf32x | libm.so.6 | — | not-started |
| GLIBC-remainderf64 | remainderf64 | libm.so.6 | — | not-started |
| GLIBC-remainderf64x | remainderf64x | libm.so.6 | — | not-started |
| GLIBC-remap_file_pages | remap_file_pages | libc.so.6 | — | not-started |
| GLIBC-removexattr | removexattr | libc.so.6 | — | not-started |
| GLIBC-remque | remque | libc.so.6 | — | not-started |
| GLIBC-remquo | remquo | libm.so.6 | — | not-started |
| GLIBC-remquof | remquof | libm.so.6 | — | not-started |
| GLIBC-remquof128 | remquof128 | libm.so.6 | — | not-started |
| GLIBC-remquof32 | remquof32 | libm.so.6 | — | not-started |
| GLIBC-remquof32x | remquof32x | libm.so.6 | — | not-started |
| GLIBC-remquof64 | remquof64 | libm.so.6 | — | not-started |
| GLIBC-remquof64x | remquof64x | libm.so.6 | — | not-started |
| GLIBC-remquol | remquol | libm.so.6 | — | not-started |
| GLIBC-renameat2 | renameat2 | libc.so.6 | — | not-started |
| GLIBC-res_dnok | res_dnok | libc.so.6 | — | not-started |
| GLIBC-res_gethostbyaddr | res_gethostbyaddr | libresolv.so.2 | GLIBC_2.2.5 | not-started |
| GLIBC-res_gethostbyname | res_gethostbyname | libresolv.so.2 | GLIBC_2.2.5 | not-started |
| GLIBC-res_gethostbyname2 | res_gethostbyname2 | libresolv.so.2 | GLIBC_2.2.5 | not-started |
| GLIBC-res_hnok | res_hnok | libc.so.6 | — | not-started |
| GLIBC-res_mailok | res_mailok | libc.so.6 | — | not-started |
| GLIBC-res_mkquery | res_mkquery | libc.so.6 | — | not-started |
| GLIBC-res_nmkquery | res_nmkquery | libc.so.6 | — | not-started |
| GLIBC-res_nquery | res_nquery | libc.so.6 | — | not-started |
| GLIBC-res_nquerydomain | res_nquerydomain | libc.so.6 | — | not-started |
| GLIBC-res_nsearch | res_nsearch | libc.so.6 | — | not-started |
| GLIBC-res_nsend | res_nsend | libc.so.6 | — | not-started |
| GLIBC-res_ownok | res_ownok | libc.so.6 | — | not-started |
| GLIBC-res_query | res_query | libc.so.6 | — | not-started |
| GLIBC-res_querydomain | res_querydomain | libc.so.6 | — | not-started |
| GLIBC-res_search | res_search | libc.so.6 | — | not-started |
| GLIBC-res_send | res_send | libc.so.6 | — | not-started |
| GLIBC-res_send_setqhook | res_send_setqhook | libresolv.so.2 | GLIBC_2.2.5 | not-started |
| GLIBC-res_send_setrhook | res_send_setrhook | libresolv.so.2 | GLIBC_2.2.5 | not-started |
| GLIBC-revoke | revoke | libc.so.6 | — | not-started |
| GLIBC-rexec | rexec | libc.so.6 | — | not-started |
| GLIBC-rexec_af | rexec_af | libc.so.6 | — | not-started |
| GLIBC-rexecoptions | rexecoptions | libc.so.6 | — | not-started |
| GLIBC-rintf128 | rintf128 | libm.so.6 | — | not-started |
| GLIBC-rintf32 | rintf32 | libm.so.6 | — | not-started |
| GLIBC-rintf32x | rintf32x | libm.so.6 | — | not-started |
| GLIBC-rintf64 | rintf64 | libm.so.6 | — | not-started |
| GLIBC-rintf64x | rintf64x | libm.so.6 | — | not-started |
| GLIBC-roundevenf128 | roundevenf128 | libm.so.6 | — | not-started |
| GLIBC-roundevenf32 | roundevenf32 | libm.so.6 | — | not-started |
| GLIBC-roundevenf32x | roundevenf32x | libm.so.6 | — | not-started |
| GLIBC-roundevenf64 | roundevenf64 | libm.so.6 | — | not-started |
| GLIBC-roundevenf64x | roundevenf64x | libm.so.6 | — | not-started |
| GLIBC-roundf128 | roundf128 | libm.so.6 | — | not-started |
| GLIBC-roundf32 | roundf32 | libm.so.6 | — | not-started |
| GLIBC-roundf32x | roundf32x | libm.so.6 | — | not-started |
| GLIBC-roundf64 | roundf64 | libm.so.6 | — | not-started |
| GLIBC-roundf64x | roundf64x | libm.so.6 | — | not-started |
| GLIBC-rpc_createerr | rpc_createerr | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-rresvport | rresvport | libc.so.6 | — | not-started |
| GLIBC-rresvport_af | rresvport_af | libc.so.6 | — | not-started |
| GLIBC-rtime | rtime | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-ruserok | ruserok | libc.so.6 | — | not-started |
| GLIBC-ruserok_af | ruserok_af | libc.so.6 | — | not-started |
| GLIBC-ruserpass | ruserpass | libc.so.6 | — | not-started |
| GLIBC-scalblnf128 | scalblnf128 | libm.so.6 | — | not-started |
| GLIBC-scalblnf32 | scalblnf32 | libm.so.6 | — | not-started |
| GLIBC-scalblnf32x | scalblnf32x | libm.so.6 | — | not-started |
| GLIBC-scalblnf64 | scalblnf64 | libm.so.6 | — | not-started |
| GLIBC-scalblnf64x | scalblnf64x | libm.so.6 | — | not-started |
| GLIBC-scalbnf128 | scalbnf128 | libm.so.6 | — | not-started |
| GLIBC-scalbnf32 | scalbnf32 | libm.so.6 | — | not-started |
| GLIBC-scalbnf32x | scalbnf32x | libm.so.6 | — | not-started |
| GLIBC-scalbnf64 | scalbnf64 | libm.so.6 | — | not-started |
| GLIBC-scalbnf64x | scalbnf64x | libm.so.6 | — | not-started |
| GLIBC-scandirat | scandirat | libc.so.6 | — | not-started |
| GLIBC-scandirat64 | scandirat64 | libc.so.6 | — | not-started |
| GLIBC-sendfile | sendfile | libc.so.6 | — | not-started |
| GLIBC-sendfile64 | sendfile64 | libc.so.6 | — | not-started |
| GLIBC-sendmmsg | sendmmsg | libc.so.6 | — | researched; netdb |
| GLIBC-setaliasent | setaliasent | libc.so.6 | — | not-started |
| GLIBC-setfsgid | setfsgid | libc.so.6 | — | not-started |
| GLIBC-setfsuid | setfsuid | libc.so.6 | — | not-started |
| GLIBC-setipv4sourcefilter | setipv4sourcefilter | libc.so.6 | — | not-started |
| GLIBC-setjmp | setjmp | libc.so.6 | — | documented; grouped |
| GLIBC-setkey | setkey | libcrypt.so.1 | GLIBC_2.2.5 | researched; cryptographic |
| GLIBC-setkey_r | setkey_r | libcrypt.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-setlogin | setlogin | libc.so.6 | — | not-started |
| GLIBC-setns | setns | libc.so.6 | — | not-started |
| GLIBC-setpayloadf128 | setpayloadf128 | libm.so.6 | — | not-started |
| GLIBC-setpayloadf32 | setpayloadf32 | libm.so.6 | — | not-started |
| GLIBC-setpayloadf32x | setpayloadf32x | libm.so.6 | — | not-started |
| GLIBC-setpayloadf64 | setpayloadf64 | libm.so.6 | — | not-started |
| GLIBC-setpayloadf64x | setpayloadf64x | libm.so.6 | — | not-started |
| GLIBC-setpayloadsigf128 | setpayloadsigf128 | libm.so.6 | — | not-started |
| GLIBC-setpayloadsigf32 | setpayloadsigf32 | libm.so.6 | — | not-started |
| GLIBC-setpayloadsigf32x | setpayloadsigf32x | libm.so.6 | — | not-started |
| GLIBC-setpayloadsigf64 | setpayloadsigf64 | libm.so.6 | — | not-started |
| GLIBC-setpayloadsigf64x | setpayloadsigf64x | libm.so.6 | — | not-started |
| GLIBC-setresgid | setresgid | libc.so.6 | — | not-started |
| GLIBC-setresuid | setresuid | libc.so.6 | — | not-started |
| GLIBC-setrpcent | setrpcent | libc.so.6 | — | not-started |
| GLIBC-setsgent | setsgent | libc.so.6 | — | not-started |
| GLIBC-setsourcefilter | setsourcefilter | libc.so.6 | — | not-started |
| GLIBC-setspent | setspent | libc.so.6 | — | not-started |
| GLIBC-setttyent | setttyent | libc.so.6 | — | not-started |
| GLIBC-setusershell | setusershell | libc.so.6 | — | not-started |
| GLIBC-setxattr | setxattr | libc.so.6 | — | not-started |
| GLIBC-sgetsgent | sgetsgent | libc.so.6 | — | not-started |
| GLIBC-sgetsgent_r | sgetsgent_r | libc.so.6 | — | not-started |
| GLIBC-sgetspent | sgetspent | libc.so.6 | — | not-started |
| GLIBC-sgetspent_r | sgetspent_r | libc.so.6 | — | not-started |
| GLIBC-shm_open | shm_open | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-shm_unlink | shm_unlink | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-shmat | shmat | libc.so.6 | — | not-started |
| GLIBC-shmctl | shmctl | libc.so.6 | — | not-started |
| GLIBC-shmdt | shmdt | libc.so.6 | — | not-started |
| GLIBC-shmget | shmget | libc.so.6 | — | not-started |
| GLIBC-sigandset | sigandset | libc.so.6 | — | not-started |
| GLIBC-siggetmask | siggetmask | libc.so.6 | — | not-started |
| GLIBC-sighold | sighold | libc.so.6 | — | not-started |
| GLIBC-sigignore | sigignore | libc.so.6 | — | not-started |
| GLIBC-sigisemptyset | sigisemptyset | libc.so.6 | — | not-started |
| GLIBC-signalfd | signalfd | libc.so.6 | — | not-started |
| GLIBC-sigorset | sigorset | libc.so.6 | — | not-started |
| GLIBC-sigqueue | sigqueue | libc.so.6 | — | not-started |
| GLIBC-sigrelse | sigrelse | libc.so.6 | — | not-started |
| GLIBC-sigreturn | sigreturn | libc.so.6 | — | not-started |
| GLIBC-sigset | sigset | libc.so.6 | — | not-started |
| GLIBC-sigtimedwait | sigtimedwait | libc.so.6 | — | documented; grouped |
| GLIBC-sigvec | sigvec | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-sigwait | sigwait | libc.so.6 | — | documented; grouped |
| GLIBC-sigwaitinfo | sigwaitinfo | libc.so.6 | — | documented; grouped |
| GLIBC-sincosf128 | sincosf128 | libm.so.6 | — | not-started |
| GLIBC-sincosf32 | sincosf32 | libm.so.6 | — | not-started |
| GLIBC-sincosf32x | sincosf32x | libm.so.6 | — | not-started |
| GLIBC-sincosf64 | sincosf64 | libm.so.6 | — | not-started |
| GLIBC-sincosf64x | sincosf64x | libm.so.6 | — | not-started |
| GLIBC-sinf128 | sinf128 | libm.so.6 | — | not-started |
| GLIBC-sinf32 | sinf32 | libm.so.6 | — | not-started |
| GLIBC-sinf32x | sinf32x | libm.so.6 | — | not-started |
| GLIBC-sinf64 | sinf64 | libm.so.6 | — | not-started |
| GLIBC-sinf64x | sinf64x | libm.so.6 | — | not-started |
| GLIBC-sinhf128 | sinhf128 | libm.so.6 | — | not-started |
| GLIBC-sinhf32 | sinhf32 | libm.so.6 | — | not-started |
| GLIBC-sinhf32x | sinhf32x | libm.so.6 | — | not-started |
| GLIBC-sinhf64 | sinhf64 | libm.so.6 | — | not-started |
| GLIBC-sinhf64x | sinhf64x | libm.so.6 | — | not-started |
| GLIBC-sinpif128 | sinpif128 | libm.so.6 | — | not-started |
| GLIBC-sinpif32 | sinpif32 | libm.so.6 | — | not-started |
| GLIBC-sinpif32x | sinpif32x | libm.so.6 | — | not-started |
| GLIBC-sinpif64 | sinpif64 | libm.so.6 | — | not-started |
| GLIBC-sinpif64x | sinpif64x | libm.so.6 | — | not-started |
| GLIBC-sockatmark | sockatmark | libc.so.6 | — | researched; netdb |
| GLIBC-splice | splice | libc.so.6 | — | not-started |
| GLIBC-sprofil | sprofil | libc.so.6 | — | not-started |
| GLIBC-sqrtf128 | sqrtf128 | libm.so.6 | — | not-started |
| GLIBC-sqrtf32 | sqrtf32 | libm.so.6 | — | not-started |
| GLIBC-sqrtf32x | sqrtf32x | libm.so.6 | — | not-started |
| GLIBC-sqrtf64 | sqrtf64 | libm.so.6 | — | not-started |
| GLIBC-sqrtf64x | sqrtf64x | libm.so.6 | — | not-started |
| GLIBC-sstk | sstk | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-statfs | statfs | libc.so.6 | — | not-started |
| GLIBC-statfs64 | statfs64 | libc.so.6 | — | not-started |
| GLIBC-statvfs | statvfs | libc.so.6 | — | not-started |
| GLIBC-statvfs64 | statvfs64 | libc.so.6 | — | not-started |
| GLIBC-statx | statx | libc.so.6 | — | not-started |
| GLIBC-stderr | stderr | libc.so.6 | — | not-started |
| GLIBC-stdin | stdin | libc.so.6 | — | not-started |
| GLIBC-stdout | stdout | libc.so.6 | — | not-started |
| GLIBC-step | step | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-strcasecmp_l | strcasecmp_l | libc.so.6 | — | not-started |
| GLIBC-strcoll_l | strcoll_l | libc.so.6 | — | not-started |
| GLIBC-strfmon_l | strfmon_l | libc.so.6 | — | documented |
| wave 7-c page (adjacent row absorbed): [strfmon.md](glibc/misc/strfmon.md) | 
| GLIBC-strfromf128 | strfromf128 | libc.so.6 | — | not-started |
| GLIBC-strfromf32 | strfromf32 | libc.so.6 | — | not-started |
| GLIBC-strfromf32x | strfromf32x | libc.so.6 | — | not-started |
| GLIBC-strfromf64 | strfromf64 | libc.so.6 | — | not-started |
| GLIBC-strfromf64x | strfromf64x | libc.so.6 | — | not-started |
| GLIBC-strncasecmp_l | strncasecmp_l | libc.so.6 | — | not-started |
| GLIBC-strptime_l | strptime_l | libc.so.6 | — | not-started |
| GLIBC-strtod_l | strtod_l | libc.so.6 | — | researched; locale-variant |
| GLIBC-strtof128 | strtof128 | libc.so.6 | — | not-started |
| GLIBC-strtof128_l | strtof128_l | libc.so.6 | — | researched; locale-variant |
| GLIBC-strtof32 | strtof32 | libc.so.6 | — | not-started |
| GLIBC-strtof32_l | strtof32_l | libc.so.6 | — | researched; locale-variant |
| GLIBC-strtof32x | strtof32x | libc.so.6 | — | not-started |
| GLIBC-strtof32x_l | strtof32x_l | libc.so.6 | — | researched; locale-variant |
| GLIBC-strtof64 | strtof64 | libc.so.6 | — | not-started |
| GLIBC-strtof64_l | strtof64_l | libc.so.6 | — | researched; locale-variant |
| GLIBC-strtof64x | strtof64x | libc.so.6 | — | not-started |
| GLIBC-strtof64x_l | strtof64x_l | libc.so.6 | — | researched; locale-variant |
| GLIBC-strtof_l | strtof_l | libc.so.6 | — | researched; locale-variant |
| GLIBC-strtol_l | strtol_l | libc.so.6 | — | researched; locale-variant |
| GLIBC-strtold_l | strtold_l | libc.so.6 | — | researched; locale-variant |
| GLIBC-strtoll_l | strtoll_l | libc.so.6 | — | researched; locale-variant |
| GLIBC-strtoul_l | strtoul_l | libc.so.6 | — | researched; locale-variant |
| GLIBC-strtoull_l | strtoull_l | libc.so.6 | — | researched; locale-variant |
| GLIBC-strxfrm_l | strxfrm_l | libc.so.6 | — | not-started |
| GLIBC-svc_exit | svc_exit | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-svc_fdset | svc_fdset | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-svc_getreq | svc_getreq | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-svc_getreq_common | svc_getreq_common | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-svc_getreq_poll | svc_getreq_poll | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-svc_getreqset | svc_getreqset | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-svc_max_pollfd | svc_max_pollfd | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-svc_pollfd | svc_pollfd | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-svc_register | svc_register | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-svc_run | svc_run | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-svc_sendreply | svc_sendreply | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-svc_unregister | svc_unregister | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-svcauthdes_stats | svcauthdes_stats | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-svcerr_auth | svcerr_auth | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-svcerr_decode | svcerr_decode | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-svcerr_noproc | svcerr_noproc | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-svcerr_noprog | svcerr_noprog | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-svcerr_progvers | svcerr_progvers | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-svcerr_systemerr | svcerr_systemerr | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-svcerr_weakauth | svcerr_weakauth | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-svcfd_create | svcfd_create | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-svcraw_create | svcraw_create | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-svctcp_create | svctcp_create | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-svcudp_bufcreate | svcudp_bufcreate | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-svcudp_create | svcudp_create | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-svcudp_enablecache | svcudp_enablecache | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-svcunix_create | svcunix_create | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-svcunixfd_create | svcunixfd_create | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-swab | swab | libc.so.6 | — | not-started |
| GLIBC-swapoff | swapoff | libc.so.6 | — | not-started |
| GLIBC-swapon | swapon | libc.so.6 | — | not-started |
| GLIBC-symlinkat | symlinkat | libc.so.6 | — | not-started |
| GLIBC-sync_file_range | sync_file_range | libc.so.6 | — | not-started |
| GLIBC-syncfs | syncfs | libc.so.6 | — | not-started |
| GLIBC-sys_errlist | sys_errlist | libc.so.6 | GLIBC_2.4 | not-started |
| GLIBC-sys_nerr | sys_nerr | libc.so.6 | GLIBC_2.4 | not-started |
| GLIBC-sys_sigabbrev | sys_sigabbrev | libc.so.6 | GLIBC_2.3.3 | not-started |
| GLIBC-sys_siglist | sys_siglist | libc.so.6 | GLIBC_2.3.3 | not-started |
| GLIBC-sysctl | sysctl | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-sysinfo | sysinfo | libc.so.6 | — | not-started |
| GLIBC-tanf128 | tanf128 | libm.so.6 | — | not-started |
| GLIBC-tanf32 | tanf32 | libm.so.6 | — | not-started |
| GLIBC-tanf32x | tanf32x | libm.so.6 | — | not-started |
| GLIBC-tanf64 | tanf64 | libm.so.6 | — | not-started |
| GLIBC-tanf64x | tanf64x | libm.so.6 | — | not-started |
| GLIBC-tanhf128 | tanhf128 | libm.so.6 | — | not-started |
| GLIBC-tanhf32 | tanhf32 | libm.so.6 | — | not-started |
| GLIBC-tanhf32x | tanhf32x | libm.so.6 | — | not-started |
| GLIBC-tanhf64 | tanhf64 | libm.so.6 | — | not-started |
| GLIBC-tanhf64x | tanhf64x | libm.so.6 | — | not-started |
| GLIBC-tanpif128 | tanpif128 | libm.so.6 | — | not-started |
| GLIBC-tanpif32 | tanpif32 | libm.so.6 | — | not-started |
| GLIBC-tanpif32x | tanpif32x | libm.so.6 | — | not-started |
| GLIBC-tanpif64 | tanpif64 | libm.so.6 | — | not-started |
| GLIBC-tanpif64x | tanpif64x | libm.so.6 | — | not-started |
| GLIBC-tee | tee | libc.so.6 | — | not-started |
| GLIBC-tgammaf128 | tgammaf128 | libm.so.6 | — | not-started |
| GLIBC-tgammaf32 | tgammaf32 | libm.so.6 | — | not-started |
| GLIBC-tgammaf32x | tgammaf32x | libm.so.6 | — | not-started |
| GLIBC-tgammaf64 | tgammaf64 | libm.so.6 | — | not-started |
| GLIBC-tgammaf64x | tgammaf64x | libm.so.6 | — | not-started |
| GLIBC-timer_create | timer_create | libc.so.6 | GLIBC_2.3.3 | not-started |
| GLIBC-timer_delete | timer_delete | libc.so.6 | GLIBC_2.3.3 | not-started |
| GLIBC-timer_getoverrun | timer_getoverrun | libc.so.6 | GLIBC_2.3.3 | not-started |
| GLIBC-timer_gettime | timer_gettime | libc.so.6 | GLIBC_2.3.3 | not-started |
| GLIBC-timer_settime | timer_settime | libc.so.6 | GLIBC_2.3.3 | not-started |
| GLIBC-timerfd_create | timerfd_create | libc.so.6 | — | not-started |
| GLIBC-timerfd_gettime | timerfd_gettime | libc.so.6 | — | not-started |
| GLIBC-timerfd_settime | timerfd_settime | libc.so.6 | — | not-started |
| GLIBC-tolower_l | tolower_l | libc.so.6 | — | researched; ctype |
| GLIBC-totalorderf128 | totalorderf128 | libm.so.6 | GLIBC_2.26 | not-started |
| GLIBC-totalorderf32 | totalorderf32 | libm.so.6 | GLIBC_2.27 | not-started |
| GLIBC-totalorderf32x | totalorderf32x | libm.so.6 | GLIBC_2.27 | not-started |
| GLIBC-totalorderf64 | totalorderf64 | libm.so.6 | GLIBC_2.27 | not-started |
| GLIBC-totalorderf64x | totalorderf64x | libm.so.6 | GLIBC_2.27 | not-started |
| GLIBC-totalordermagf128 | totalordermagf128 | libm.so.6 | GLIBC_2.26 | not-started |
| GLIBC-totalordermagf32 | totalordermagf32 | libm.so.6 | GLIBC_2.27 | not-started |
| GLIBC-totalordermagf32x | totalordermagf32x | libm.so.6 | GLIBC_2.27 | not-started |
| GLIBC-totalordermagf64 | totalordermagf64 | libm.so.6 | GLIBC_2.27 | not-started |
| GLIBC-totalordermagf64x | totalordermagf64x | libm.so.6 | GLIBC_2.27 | not-started |
| GLIBC-toupper_l | toupper_l | libc.so.6 | — | researched; ctype |
| GLIBC-towctrans_l | towctrans_l | libc.so.6 | — | researched; ctype |
| GLIBC-towlower_l | towlower_l | libc.so.6 | — | researched; ctype |
| GLIBC-towupper_l | towupper_l | libc.so.6 | — | researched; ctype |
| GLIBC-tr_break | tr_break | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-truncf128 | truncf128 | libm.so.6 | — | not-started |
| GLIBC-truncf32 | truncf32 | libm.so.6 | — | not-started |
| GLIBC-truncf32x | truncf32x | libm.so.6 | — | not-started |
| GLIBC-truncf64 | truncf64 | libm.so.6 | — | not-started |
| GLIBC-truncf64x | truncf64x | libm.so.6 | — | not-started |
| GLIBC-ttyslot | ttyslot | libc.so.6 | — | not-started |
| GLIBC-ualarm | ualarm | libc.so.6 | — | not-started |
| GLIBC-ufromfpf128 | ufromfpf128 | libm.so.6 | — | not-started |
| GLIBC-ufromfpf32 | ufromfpf32 | libm.so.6 | — | not-started |
| GLIBC-ufromfpf32x | ufromfpf32x | libm.so.6 | — | not-started |
| GLIBC-ufromfpf64 | ufromfpf64 | libm.so.6 | — | not-started |
| GLIBC-ufromfpf64x | ufromfpf64x | libm.so.6 | — | not-started |
| GLIBC-ufromfpxf128 | ufromfpxf128 | libm.so.6 | — | not-started |
| GLIBC-ufromfpxf32 | ufromfpxf32 | libm.so.6 | — | not-started |
| GLIBC-ufromfpxf32x | ufromfpxf32x | libm.so.6 | — | not-started |
| GLIBC-ufromfpxf64 | ufromfpxf64 | libm.so.6 | — | not-started |
| GLIBC-ufromfpxf64x | ufromfpxf64x | libm.so.6 | — | not-started |
| GLIBC-ulckpwdf | ulckpwdf | libc.so.6 | — | not-started |
| GLIBC-unshare | unshare | libc.so.6 | — | not-started |
| GLIBC-updwtmpx | updwtmpx | libc.so.6 | — | not-started |
| GLIBC-uselib | uselib | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-uselocale | uselocale | libc.so.6 | — | documented; Grouped |
| GLIBC-user2netname | user2netname | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-usleep | usleep | libc.so.6 | — | documented; triage |
| GLIBC-ustat | ustat | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-vhangup | vhangup | libc.so.6 | — | not-started |
| GLIBC-vmsplice | vmsplice | libc.so.6 | — | not-started |
| GLIBC-vtimes | vtimes | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-waitid | waitid | libc.so.6 | — | documented; full |
| GLIBC-wcscasecmp_l | wcscasecmp_l | libc.so.6 | — | not-started |
| GLIBC-wcscoll_l | wcscoll_l | libc.so.6 | — | not-started |
| GLIBC-wcsftime_l | wcsftime_l | libc.so.6 | — | documented |
| wave 7-c page (adjacent row absorbed): [wcsftime.md](glibc/misc/wcsftime.md) | 
| GLIBC-wcsncasecmp_l | wcsncasecmp_l | libc.so.6 | — | not-started |
| GLIBC-wcstod_l | wcstod_l | libc.so.6 | — | researched; locale-variant |
| GLIBC-wcstof128 | wcstof128 | libc.so.6 | — | not-started |
| GLIBC-wcstof128_l | wcstof128_l | libc.so.6 | — | researched; locale-variant |
| GLIBC-wcstof32 | wcstof32 | libc.so.6 | — | not-started |
| GLIBC-wcstof32_l | wcstof32_l | libc.so.6 | — | researched; locale-variant |
| GLIBC-wcstof32x | wcstof32x | libc.so.6 | — | not-started |
| GLIBC-wcstof32x_l | wcstof32x_l | libc.so.6 | — | researched; locale-variant |
| GLIBC-wcstof64 | wcstof64 | libc.so.6 | — | not-started |
| GLIBC-wcstof64_l | wcstof64_l | libc.so.6 | — | researched; locale-variant |
| GLIBC-wcstof64x | wcstof64x | libc.so.6 | — | not-started |
| GLIBC-wcstof64x_l | wcstof64x_l | libc.so.6 | — | researched; locale-variant |
| GLIBC-wcstof_l | wcstof_l | libc.so.6 | — | researched; locale-variant |
| GLIBC-wcstol_l | wcstol_l | libc.so.6 | — | researched; locale-variant |
| GLIBC-wcstold_l | wcstold_l | libc.so.6 | — | researched; locale-variant |
| GLIBC-wcstoll_l | wcstoll_l | libc.so.6 | — | researched; locale-variant |
| GLIBC-wcstoul_l | wcstoul_l | libc.so.6 | — | researched; locale-variant |
| GLIBC-wcstoull_l | wcstoull_l | libc.so.6 | — | researched; locale-variant |
| GLIBC-wcswidth | wcswidth | libc.so.6 | — | researched; character |
| GLIBC-wcsxfrm_l | wcsxfrm_l | libc.so.6 | — | not-started |
| GLIBC-wctrans_l | wctrans_l | libc.so.6 | — | researched; ctype |
| GLIBC-wctype_l | wctype_l | libc.so.6 | — | researched; ctype |
| GLIBC-wcwidth | wcwidth | libc.so.6 | — | researched; character |
| GLIBC-writeColdStartFile | writeColdStartFile | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-xcrypt | xcrypt | libcrypt.so.1 | — | not-started |
| GLIBC-xcrypt_gensalt | xcrypt_gensalt | libcrypt.so.1 | — | not-started |
| GLIBC-xcrypt_gensalt_r | xcrypt_gensalt_r | libcrypt.so.1 | — | not-started |
| GLIBC-xcrypt_r | xcrypt_r | libcrypt.so.1 | — | not-started |
| GLIBC-xdecrypt | xdecrypt | libc.so.6 | GLIBC_2.2.5 | researched; crypt |
| GLIBC-xdr_accepted_reply | xdr_accepted_reply | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_array | xdr_array | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_authdes_cred | xdr_authdes_cred | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_authdes_verf | xdr_authdes_verf | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_authunix_parms | xdr_authunix_parms | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_bool | xdr_bool | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_bytes | xdr_bytes | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_callhdr | xdr_callhdr | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_callmsg | xdr_callmsg | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_cback_data | xdr_cback_data | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_char | xdr_char | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_cryptkeyarg | xdr_cryptkeyarg | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_cryptkeyarg2 | xdr_cryptkeyarg2 | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_cryptkeyres | xdr_cryptkeyres | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_des_block | xdr_des_block | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_domainname | xdr_domainname | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_double | xdr_double | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_enum | xdr_enum | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_float | xdr_float | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_free | xdr_free | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_getcredres | xdr_getcredres | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_hyper | xdr_hyper | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_int | xdr_int | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_int16_t | xdr_int16_t | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_int32_t | xdr_int32_t | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_int64_t | xdr_int64_t | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_int8_t | xdr_int8_t | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_key_netstarg | xdr_key_netstarg | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_key_netstres | xdr_key_netstres | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_keybuf | xdr_keybuf | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_keydat | xdr_keydat | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_keystatus | xdr_keystatus | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_long | xdr_long | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_longlong_t | xdr_longlong_t | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_mapname | xdr_mapname | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_netnamestr | xdr_netnamestr | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_netobj | xdr_netobj | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_obj_p | xdr_obj_p | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_opaque | xdr_opaque | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_opaque_auth | xdr_opaque_auth | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_peername | xdr_peername | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_pmap | xdr_pmap | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_pmaplist | xdr_pmaplist | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_pointer | xdr_pointer | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_quad_t | xdr_quad_t | libc.so.6 | GLIBC_2.3.4 | not-started |
| GLIBC-xdr_reference | xdr_reference | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_rejected_reply | xdr_rejected_reply | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_replymsg | xdr_replymsg | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_rmtcall_args | xdr_rmtcall_args | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_rmtcallres | xdr_rmtcallres | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_short | xdr_short | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_sizeof | xdr_sizeof | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_string | xdr_string | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_u_char | xdr_u_char | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_u_hyper | xdr_u_hyper | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_u_int | xdr_u_int | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_u_long | xdr_u_long | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_u_longlong_t | xdr_u_longlong_t | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_u_quad_t | xdr_u_quad_t | libc.so.6 | GLIBC_2.3.4 | not-started |
| GLIBC-xdr_u_short | xdr_u_short | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_uint16_t | xdr_uint16_t | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_uint32_t | xdr_uint32_t | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_uint64_t | xdr_uint64_t | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_uint8_t | xdr_uint8_t | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_union | xdr_union | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_unixcred | xdr_unixcred | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_valdat | xdr_valdat | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_vector | xdr_vector | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_void | xdr_void | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_wrapstring | xdr_wrapstring | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_yp_buf | xdr_yp_buf | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_ypall | xdr_ypall | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_ypbind_binding | xdr_ypbind_binding | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_ypbind_resp | xdr_ypbind_resp | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_ypbind_resptype | xdr_ypbind_resptype | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_ypbind_setdom | xdr_ypbind_setdom | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_ypdelete_args | xdr_ypdelete_args | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_ypmap_parms | xdr_ypmap_parms | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_ypmaplist | xdr_ypmaplist | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_yppush_status | xdr_yppush_status | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_yppushresp_xfr | xdr_yppushresp_xfr | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_ypreq_key | xdr_ypreq_key | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_ypreq_nokey | xdr_ypreq_nokey | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_ypreq_xfr | xdr_ypreq_xfr | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_ypresp_all | xdr_ypresp_all | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_ypresp_key_val | xdr_ypresp_key_val | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_ypresp_maplist | xdr_ypresp_maplist | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_ypresp_master | xdr_ypresp_master | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_ypresp_order | xdr_ypresp_order | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_ypresp_val | xdr_ypresp_val | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_ypresp_xfr | xdr_ypresp_xfr | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_ypstat | xdr_ypstat | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_ypupdate_args | xdr_ypupdate_args | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-xdr_ypxfrstat | xdr_ypxfrstat | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-xdrmem_create | xdrmem_create | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-xdrrec_create | xdrrec_create | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-xdrrec_endofrecord | xdrrec_endofrecord | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-xdrrec_eof | xdrrec_eof | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-xdrrec_skiprecord | xdrrec_skiprecord | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-xdrstdio_create | xdrstdio_create | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-xencrypt | xencrypt | libc.so.6 | GLIBC_2.2.5 | researched; crypt |
| GLIBC-xprt_register | xprt_register | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-xprt_unregister | xprt_unregister | libc.so.6 | GLIBC_2.2.5 | not-started |
| GLIBC-y0f128 | y0f128 | libm.so.6 | — | not-started |
| GLIBC-y0f32 | y0f32 | libm.so.6 | — | not-started |
| GLIBC-y0f32x | y0f32x | libm.so.6 | — | not-started |
| GLIBC-y0f64 | y0f64 | libm.so.6 | — | not-started |
| GLIBC-y0f64x | y0f64x | libm.so.6 | — | not-started |
| GLIBC-y1f128 | y1f128 | libm.so.6 | — | not-started |
| GLIBC-y1f32 | y1f32 | libm.so.6 | — | not-started |
| GLIBC-y1f32x | y1f32x | libm.so.6 | — | not-started |
| GLIBC-y1f64 | y1f64 | libm.so.6 | — | not-started |
| GLIBC-y1f64x | y1f64x | libm.so.6 | — | not-started |
| GLIBC-ynf128 | ynf128 | libm.so.6 | — | not-started |
| GLIBC-ynf32 | ynf32 | libm.so.6 | — | not-started |
| GLIBC-ynf32x | ynf32x | libm.so.6 | — | not-started |
| GLIBC-ynf64 | ynf64 | libm.so.6 | — | not-started |
| GLIBC-ynf64x | ynf64x | libm.so.6 | — | not-started |
| GLIBC-yp_all | yp_all | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-yp_bind | yp_bind | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-yp_first | yp_first | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-yp_get_default_domain | yp_get_default_domain | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-yp_maplist | yp_maplist | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-yp_master | yp_master | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-yp_match | yp_match | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-yp_next | yp_next | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-yp_order | yp_order | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-yp_unbind | yp_unbind | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-yp_update | yp_update | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-ypbinderr_string | ypbinderr_string | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-yperr_string | yperr_string | libnsl.so.1 | GLIBC_2.2.5 | not-started |
| GLIBC-ypprot_err | ypprot_err | libnsl.so.1 | GLIBC_2.2.5 | not-started |
