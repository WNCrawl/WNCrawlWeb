from datetime import datetime
from datetime import timedelta


def split_args(args, fix_type):
    if fix_type == 1:
        assert "start_date" in args or "end_date" in args
        start_date_arg = args["start_date"]
        end_date_arg = args["end_date"]
        start_date = datetime.strptime(start_date_arg, "%Y-%m-%d")
        end_date = datetime.strptime(end_date_arg, "%Y-%m-%d")

        args_list = list()
        while 1:
            current_date = start_date
            start_date = start_date + timedelta(days=1)
            args_list.append({"start_date": current_date.strftime("%Y-%m-%d"),
                              "end_date": start_date.strftime("%Y-%m-%d")})
            if (end_date - start_date).days == 0:
                break
        return args_list


print(split_args({"start_date": "2018-09-25", "end_date": "2018-10-02"}, fix_type=1))
