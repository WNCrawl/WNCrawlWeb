# -*- coding: utf-8 -*-


def update_model(model, check_args, **kwargs):
    records = model.objects.filter(**check_args)
    if records.exists():
        r = records[0]
        update_fields = []
        for k in kwargs.keys():
            if getattr(r, k) != kwargs.get(k):
                setattr(r, k, kwargs.get(k))
                update_fields.append(k)
        r.save(update_fields=update_fields)
    else:
        for k, v in check_args.iteritems():
            kwargs[k] = v
        model.objects.create(**kwargs)