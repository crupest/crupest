require ["copy", "environment", "imapsieve", "vnd.dovecot.pipe"];

if anyof(
  environment "imap.mailbox" "Junk",
  environment "imap.mailbox" "Trash"
) {
  stop;
}

pipe :copy "learn-ham";
