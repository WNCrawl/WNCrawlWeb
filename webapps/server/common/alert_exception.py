from apps.alert.models import CrawlUserAlertRel, CrawlAlert
from apps.user.models import CrawlUser
from server.common import wx_tools


class AlertException(Exception):
    def __init__(self, *args):
        self.args = args

        alert_id = args[0].value
        alert_content = args[1]
        rels = CrawlUserAlertRel.objects.filter(alert_id=alert_id, is_deleted=0)
        alert_title = CrawlAlert.objects.get(is_deleted=0, id=alert_id).alert_name
        to_user_id_list = list(map(lambda x: x.user_id, rels))
        to_user_list = CrawlUser.objects.filter(id__in=to_user_id_list)
        to_user_wx_account = list(map(lambda x: x.wx_account, to_user_list))
        to_user = '|'.join(str(user_id) for user_id in to_user_wx_account)
        wx_tools.env_send_card_message(to_user, alert_title, alert_content)
        # TODO 这里要加进告警记录中
