from scrapyd_api import ScrapydAPI


# sa = ScrapydAPI("http://bigdata.robam.com:6800", timeout=30)
#
# jobs_json = sa.list_jobs("sycm")
#
# running_jobs = jobs_json["running"]
#
# for rj in running_jobs:
#     jid = rj["id"]
#     sa.cancel("sycm", jid)


db_job_ids = [3,5, 1, 7]
redis_job_ids = [1, 4]
c_ids = [i for i in redis_job_ids if i not in db_job_ids]
print(c_ids)