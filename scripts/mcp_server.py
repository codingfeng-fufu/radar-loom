#!/usr/bin/env python3
"""Minimal stdio MCP adapter for the local knowledge base (stdlib only)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from serve_kb import KnowledgeBuilder, catalog_payload, health_summary, page_history_payload, search_payload


ROOT = Path(__file__).resolve().parent.parent
BUILDER = KnowledgeBuilder(ROOT)


def result(request_id, value):
    return {'jsonrpc': '2.0', 'id': request_id, 'result': {'content': [{'type': 'text', 'text': json.dumps(value, ensure_ascii=False)}]}}


def error(request_id, message):
    return {'jsonrpc': '2.0', 'id': request_id, 'error': {'code': -32602, 'message': message}}


def dispatch(request):
    request_id = request.get('id')
    method = request.get('method')
    params = request.get('params') or {}
    if method == 'initialize':
        return result(request_id, {'protocolVersion': '2024-11-05', 'serverInfo': {'name': 'technical-radar-kb', 'version': '1.0'}, 'capabilities': {'tools': {}}})
    if method == 'tools/list':
        return result(request_id, {'tools': [
            {'name': 'kb_search', 'description': 'Search full page text', 'inputSchema': {'type': 'object', 'properties': {'query': {'type': 'string'}, 'section': {'type': 'string'}}, 'required': ['query']}},
            {'name': 'kb_catalog', 'description': 'Read graph catalog', 'inputSchema': {'type': 'object'}},
            {'name': 'kb_health', 'description': 'Read local health summary', 'inputSchema': {'type': 'object'}},
            {'name': 'kb_page_history', 'description': 'Read Git history for a page', 'inputSchema': {'type': 'object', 'properties': {'file': {'type': 'string'}}, 'required': ['file']}},
        ]})
    if method != 'tools/call':
        return result(request_id, {})
    name = params.get('name'); arguments = params.get('arguments') or {}
    try:
        if name == 'kb_search':
            value = search_payload(ROOT, str(arguments.get('query', '')), str(arguments.get('section', '')))
        elif name == 'kb_catalog':
            value = catalog_payload(json.loads((ROOT / 'graph-data.json').read_text(encoding='utf-8')), json.loads((ROOT / 'interview-graph-data.json').read_text(encoding='utf-8')))
        elif name == 'kb_health':
            value = health_summary(ROOT, BUILDER)
        elif name == 'kb_page_history':
            value = page_history_payload(ROOT, str(arguments.get('file', '')))
        else:
            return error(request_id, f'unknown tool: {name}')
        return result(request_id, value)
    except Exception as exc:  # MCP boundary: return structured error, keep process alive.
        return error(request_id, str(exc))


for line in sys.stdin:
    try:
        request = json.loads(line)
        print(json.dumps(dispatch(request), ensure_ascii=False), flush=True)
    except json.JSONDecodeError as exc:
        print(json.dumps(error(None, str(exc)), ensure_ascii=False), flush=True)
