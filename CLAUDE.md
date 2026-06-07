# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a cross-platform application built with the **UniApp** framework (Vue.js-based, by DCloud). It targets iOS, Android, Web (H5), and various mini-program platforms.

## Tech Stack

- **Framework:** UniApp (Vue 3 + Composition API)
- **Language:** TypeScript
- **Linting:** ESLint + TSLint
- **Package Manager:** npm
- **IDE:** WebStorm/IntelliJ (JetBrains)

## Commands

The project is currently in its initial state with no `package.json` or source files. Common UniApp commands once configured:

```bash
# Development
npm run dev:h5          # Web/H5 dev server
npm run dev:mp-weixin   # WeChat mini-program dev
npm run dev:app-plus    # Native app dev

# Build
npm run build:h5
npm run build:mp-weixin
npm run build:app-plus

# Linting
npm run lint
```

## Architecture

Standard UniApp project structure (once created):

```
src/
  pages/            # Page components (referenced in pages.json)
  components/       # Reusable Vue components
  static/           # Static assets
  App.vue           # Root Vue component
  main.js           # Entry point
  manifest.json     # App configuration
pages.json          # Page routing and window config
uni.scss            # Global SCSS variables
package.json        # Dependencies and scripts
```

Key UniApp conventions:
- Page routing is configured declaratively in `pages.json`, not via vue-router
- Platform-specific code uses conditional compilation: `#ifdef H5`, `#ifdef MP-WEIXIN`, `#ifdef APP-PLUS`
- The `uni` global API provides cross-platform equivalents for network requests, storage, UI, etc.
