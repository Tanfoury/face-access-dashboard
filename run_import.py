import traceback
try:
    import dashboard
    print('IMPORT_OK')
except Exception as e:
    print('IMPORT_ERROR', e)
    traceback.print_exc()
