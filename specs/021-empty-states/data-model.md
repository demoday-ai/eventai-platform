# Data Model: Empty States и подсказки

**Feature**: 021-empty-states
**Date**: 2026-02-09

## Overview

This is a frontend-only feature. No new database entities or API endpoints are required. The feature uses existing API data to determine when to show empty states.

## Component Interface

### PageEmptyState Props

| Prop | Type | Required | Description |
|------|------|----------|-------------|
| icon | LucideIcon | Yes | Lucide icon component to display |
| title | string | Yes | Main heading text |
| description | string | Yes | Explanatory text below the title |
| actionLabel | string | No | Button label (if action available) |
| actionLink | string | No | Route path for the action button |

### Pipeline Dependency Map

| Page | Depends On | Check Method | Empty State Trigger |
|------|-----------|-------------|-------------------|
| ProjectsList | Projects loaded | `getProjects()` returns empty array | 0 projects and no search/filter active |
| Clustering | Projects loaded | `getProjects()` count or existing query | 0 projects in system |
| ExpertMatching | Approved clustering | `getCurrentClustering()` returns null/404 or not approved | No clustering or not approved |
| Schedule | Approved clustering | `getCurrentClustering()` returns null/404 or not approved | No clustering or not approved |
| Messaging | Event exists + Participants exist | `getDashboard()` or `isNoEventError` + participant counts | No event OR 0 participants |
| GuestList | Event exists + Contacts exist | `getGuests()` returns empty + `isNoEventError` | No event OR 0 guests |

## No Database Changes

No Alembic migrations needed. No new models or schemas.
