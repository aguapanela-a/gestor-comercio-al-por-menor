from app.core.health import check_all_databases

results = check_all_databases()

for result in results:
    if result["connected"]:
        print(result["service"] + ": CONECTADO")
    else:
        print(result["service"] + ": ERROR - " + str(result["error"])[:250])
