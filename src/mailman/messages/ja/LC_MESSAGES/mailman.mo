��          �      <      �  �   �     q     �     �     �  /   �  1   �     .     ;     R     c     t  L   �  F   �  R     S   r  !   �  �  �    �     �     �     �     �  "   �  (        @  *   O     z     �     �  \   �  L   !	  b   n	  e   �	  <   7
                                                              
                                   	        Configuration file to use.  If not given, the environment variable
    MAILMAN_CONFIG_FILE is consulted and used if set.  If neither are given, a
    default configuration file is loaded.     Date: ${date}     From: ${from_}     Message-ID: ${message_id}     Subject: ${subject} ${mlist.display_name} subscription notification ${mlist.display_name} unsubscription notification (no subject) Message has no subject Original Message Today's Topics:
 Unsubscription request You have been invited to join the ${event.mlist.fqdn_listname} mailing list. You have been unsubscribed from the ${mlist.display_name} mailing list Your confirmation is needed to join the ${event.mlist.fqdn_listname} mailing list. Your confirmation is needed to leave the ${event.mlist.fqdn_listname} mailing list. list:admin:notice:unsubscribe.txt Project-Id-Version: PACKAGE VERSION
Report-Msgid-Bugs-To: 
PO-Revision-Date: 2022-03-23 03:39+0000
Last-Translator: Shohei Kusakata <shohei@kusakata.com>
Language-Team: Japanese <https://hosted.weblate.org/projects/gnu-mailman/mailman/ja/>
Language: ja
MIME-Version: 1.0
Content-Type: text/plain; charset=UTF-8
Content-Transfer-Encoding: 8bit
Plural-Forms: nplurals=1; plural=0;
X-Generator: Weblate 4.12-dev
     使用する設定ファイル。  指定しなかった場合、環境変数
    MAILMAN_CONFIG_FILE が確認され設定されている場合使用されます。  どちらも未設定の場合、
    デフォルトの設定ファイルがロードされます。     日付: ${date}     送信元: ${from_}     Message-ID: ${message_id}     題名: ${subject} ${mlist.display_name} 購読通知 ${mlist.display_name} 購読解除通知 (題名なし) メッセージに題名がありません 元のメッセージ 今日のトピック:
 購読解除リクエスト ${event.mlist.fqdn_listname} メーリングリストへの参加を招待されました。 ${mlist.display_name} メーリングリストの購読を解除しました ${event.mlist.fqdn_listname} メーリングリストに参加するには確認が必要です。 ${event.mlist.fqdn_listname} メーリングリストから脱退するには確認が必要です。 ${member} は ${display_name} から削除されました。 