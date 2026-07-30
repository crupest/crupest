export const handler = async (event, context, callback) => {
  const sesNotification = event.Records[0].ses;
  console.log("SES Notification:\n", JSON.stringify(sesNotification, null, 2));

  const res = await fetch(
    `https://mail.crupest.life/${process.env.CRUPEST_MAIL_SERVER_AWS_INBOUND_PATH}`,
    {
      method: "POST",
      headers: {
        "content-type": "application/json",
        "Authorization": process.env.CRUPEST_MAIL_SERVER_AWS_INBOUND_KEY,
      },
      body: JSON.stringify({
        key: sesNotification.mail.messageId,
        recipients: sesNotification.receipt.recipients,
      }),
    },
  );
  console.log(res);
  console.log(res.text());

  callback(null, { "disposition": "CONTINUE" });
};
