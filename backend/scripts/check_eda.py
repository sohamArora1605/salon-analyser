import urllib.request, json, pprint
url='http://localhost:8000/api/analytics/eda'
try:
    with urllib.request.urlopen(url, timeout=10) as r:
        j=json.load(r)
        print('OK, keys:', sorted(j.keys()))
        keys=['revenue_by_weekday','appointments_by_month','revenue_by_month','top_staff_revenue','client_frequency_segments']
        pprint.pprint({k:j.get(k) for k in keys})
except Exception as e:
    print('ERROR', e)
    raise
