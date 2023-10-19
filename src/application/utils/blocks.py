def alarm_blocks(alarm: dict):
    blocks = [
		{
			"type": "header",
			"text": {
				"type": "plain_text",
				"text": "The alarm has arrived!",
				"emoji": True
			}
		},
		{
			"type": "section",
			"fields": [
         		{
					"type": "mrkdwn",
					"text": f"*Content:*\n{alarm['content']}",
				},
        	    {
					"type": "mrkdwn",
					"text": f"*Deadline:*\n{alarm['deadline']}",
				},
				{
					"type": "mrkdwn",
					"text": f"*Notification Time:*\n{alarm['alarm_date']}",
				},
				{
					"type": "mrkdwn",
					"text": f"*Interval:*\n{alarm['interval']}"
				},
			]
		},
		{
			"type": "section",
			"text": {
				"type": "plain_text",
				"text": "If you have checked the alarm, press Check or Delete button to delete the alarm",
				"emoji": True
			}
		},
		{
			"type": "actions",
			"elements": [
				{
					"type": "button",
					"text": {
						"type": "plain_text",
						"emoji": True,
						"text": "Check"
					},
					"style": "primary",
					"value": "click_me_123"
				},
				{
					"type": "button",
					"text": {
						"type": "plain_text",
						"emoji": True,
						"text": "Delete"
					},
					"style": "danger",
					"value": "click_me_123"
				}
			]
		}
	]
    return blocks


def click_delete_button_blocks(text: str):
    blocks = [
		{
			"type": "header",
			"text": {
				"type": "plain_text",
				"text": text,
				"emoji": True
			}
		},
		{
			"type": "section",
			"text": {
				"type": "plain_text",
				"text": "Alarm has been deleted.",
				"emoji": True
			}
		},
	]
    return blocks


def click_check_button_blocks(text: str):
    blocks = [
		{
			"type": "header",
			"text": {
				"type": "plain_text",
				"text": text,
				"emoji": True
			}
		},
		{
			"type": "section",
			"text": {
				"type": "plain_text",
				"text": "Checked the alarm.",
				"emoji": True
			}
		},
	]
    return blocks


def app_home_opened_view_blocks():
    return {
		"type": "home",
		"callback_id": "home_view",
		
		"blocks": [
			{
				"type": "header",
				"text": {
					"type": "plain_text",
					"text": "Welcome to the Sigan Alarm App!"
				}
       		},
   			{
				"type": "divider"
			},
			{
				"type": "section",
				"text": {
					"type": "mrkdwn",
					"text": "This app is a convenient app that allows you to set alarms through a simple CLI. Create an alarm on the slack with a simple command!"
				}
			},
		]
	}