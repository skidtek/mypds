# 0002. Vue 3, TypeScript and Vite for the interface

Status: accepted

## Context
The interface is rich (two layout editors, themes, live tiles) but is served as static files by the back end. Nothing should need Node.js in production.

## Decision
Vue 3 with `<script setup>`, strict TypeScript, Vite, Pinia and Vue Router. Plain modern CSS (custom properties, container queries) and no CSS framework. Phosphor icons, and the Inter font served locally. Translations use a small in-house helper: French source strings are the keys, and a test checks that the English catalog covers them all.

## Consequences
- A light bundle, built once on the developer's machine or in CI.
- No server-side rendering. First paint needs JavaScript, which is fine on a LAN.
- Using French strings as keys keeps the code readable for the original author. Adding a language means adding one catalog file.
