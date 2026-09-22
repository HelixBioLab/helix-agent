# RepeatsDB admission audit — 2026-09-21

The current official [license page](https://repeatsdb.org/about/license), resolved through the website's current Angular about-module bundle, declares CC BY 4.0. The earlier statement that only the archived website carries a license is outdated. Its displayed wording is: “This work is licensed under a Creative Commons Attribution 4.0 International License.” The OpenAPI document does not separately state a license or define the scope of this notice for individual API records.

The current [official API schema](https://repeatsdb.org/api/) defines annotation loci as generic objects. Its example uses start `0` and end `100`, without defining author numbering, label numbering, origin, inclusive endpoints or insertion-code handling. The current frontend's structural parser reads `auth_seq_id`; this alone does not establish the coordinate frame of API annotation loci.

Decision: retain the existing admission restriction for automatic geometry composition. Do not infer a global numbering convention from one compatible record. An explicitly validated record-level coordinate mapping remains necessary. This audit changes no catalog data.

`audit.json` contains retrieval time, official source URLs, content hashes, schema excerpts and the distinction between observed facts and unresolved interpretation. No external contacts or write API requests were made.
