"""The %%unloop cell magic for Jupyter notebooks."""

import contextlib
import io

from unloop.optimizer import optimize


def load_ipython_extension(ipython):
    """Called by Jupyter when the user runs: %load_ext unloop"""

    def unloop_magic(line, cell):
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                result = optimize(cell, ipython.user_ns, use_ai="--no-ai" not in line)
        except Exception as error:
            print(f"unloop: could not analyze this cell ({error}). Running it unchanged.")
            ipython.run_cell(cell)
            return

        status = result["status"]
        if status == "optimized" and result["verdict"] == "identical":
            print(f"unloop: {result['speedup']:.0f}x faster via {result['source']}, results identical. Running:")
            print(result["code"])
            ipython.run_cell(result["code"])
        elif status == "optimized":
            print(f"unloop: {result['speedup']:.0f}x faster via {result['source']}, but data types change:")
            for note in result["notes"]:
                print("  " + note)
            print("Suggested code (not applied):")
            print(result["code"])
            ipython.run_cell(cell)
        else:
            print(f"unloop: no safe speedup found ({status}). Running cell unchanged.")
            ipython.run_cell(cell)

    ipython.register_magic_function(unloop_magic, magic_kind="cell", magic_name="unloop")