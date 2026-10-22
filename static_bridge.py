"""Run the pinned upstream engine in an isolated Python process.

Only the engine directory is added to sys.path; target code is never imported.
"""
import argparse
from pathlib import Path
import sys


def run(snapshot, output, commit, source_roots=None):
    sys.path.insert(0, str(Path(__file__).resolve().parent / 'static_analysis'))
    from ast_parser import scan_repository
    from symbol_builder import build_symbol_result, save_json
    from graph_builder import build_graph
    from graph_report import write_html
    from unresolved_classifier import reclassify_graph, write_classification
    from call_status import annotate_call_statuses, write_call_statuses

    out = Path(output)
    out.mkdir(parents=True, exist_ok=True)
    ast_data = scan_repository(snapshot, source_roots=source_roots)
    ast_data['commit'] = commit
    symbols = build_symbol_result(ast_data)
    symbols['commit'] = commit
    graph = annotate_call_statuses(reclassify_graph(build_graph(symbols), symbols), symbols)
    graph['commit'] = commit
    for name, data in [('ast_result', ast_data), ('symbol_result', symbols), ('graph_result', graph)]:
        save_json(data, out / (name + '.json'))
    write_classification(graph, out)
    write_call_statuses(graph, out)
    write_html(graph, out / 'report.html')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('snapshot')
    p.add_argument('output')
    p.add_argument('commit')
    p.add_argument('--source-root', action='append')
    a = p.parse_args()
    run(a.snapshot, a.output, a.commit, a.source_root)
