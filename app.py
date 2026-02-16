KeyError: This app has encountered an error. The original error message is redacted to prevent data leaks. Full error details have been recorded in the logs (if you're on Streamlit Cloud, click on 'Manage app' in the lower right of your app).
Traceback:
File "/mount/src/turnazione-guardia-medica/app.py", line 105, in <module>
    df_ed.drop(columns=["hM","hP","hN","FESTIVO"]).to_excel(writer, index=False)
    ~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
File "/home/adminuser/venv/lib/python3.13/site-packages/pandas/core/frame.py", line 5603, in drop
    return super().drop(
           ~~~~~~~~~~~~^
        labels=labels,
        ^^^^^^^^^^^^^^
    ...<5 lines>...
        errors=errors,
        ^^^^^^^^^^^^^^
    )
    ^
File "/home/adminuser/venv/lib/python3.13/site-packages/pandas/core/generic.py", line 4810, in drop
    obj = obj._drop_axis(labels, axis, level=level, errors=errors)
File "/home/adminuser/venv/lib/python3.13/site-packages/pandas/core/generic.py", line 4852, in _drop_axis
    new_axis = axis.drop(labels, errors=errors)
File "/home/adminuser/venv/lib/python3.13/site-packages/pandas/core/indexes/base.py", line 7136, in drop
    raise KeyError(f"{labels[mask].tolist()} not found in axis")
