require ["fileinto", "vnd.dovecot.filter"];

filter "spamc";

if header :is "X-Spam-Flag" "YES" {
  fileinto "Junk";
  stop;
}
