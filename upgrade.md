# Upgrade Guide

An upgrade can be done in one of two ways, depending on how Zpark was
installed. After following the instructions below, read the section below
for the version you're upgrading to for version-specific instructions.

The very last step is to restart the Zpark API and Celery worker processes.

```
# supervisorctl restart zpark zpark_celery
```

### Installed using a git clone

Use git to sync with the Zpark Github repo and then checkout the latest
version by specifying the correct tag.

```
% cd /home/zpark/zpark
% git fetch
% git checkout v1.2.0
```

Now read the section below for the version you're upgrading to for
version-specific instructions.

### Installed by downloading a release

Download the latest release from
[the list of releases](https://github.com/knightjoel/zpark/releases)
and extract the archive. It will extract into its own directory which you'll
need to rename to `zpark`. **Do not delete your `app.cfg` file**; copy it
from your old installation to the new one.

```
% <download the release>
% cd /home/zpark
% tar zxf ~/v1.2.0.tar.gz
% mv zpark zpark-old
% mv zpark-1.2.0 zpark
% cp zpark-old/app.cfg zpark/app.cfg
```

When you're satisfied that you don't need to rollback to the old version,
you may delete the `zpark-old` directory.

Now read the section below for the version you're upgrading to for version-
specific instructions.

# Upgrade Notes

### To v1.2.1

This release is mostly bug and security fixes.

There is a new setting `ZABBIX_TLS_CERT_VERIFY` which controls whether
Zpark will verify the TLS certificate served up by Zabbix (when Zabbix is
configured for HTTPS). Set this to `False` when Zabbix is using a self-signed
certificate.

There are no special considerations for upgrading to v1.2.1.

Read the [v1.2.0 release notes](relnotes.html#v120) and 
[v1.2.1 release notes](relnotes.html#v121) for more information.

### v1.0.0 to v1.1.0

- There is a new config setting named `ZPARK_CONTACT_INFO` which you may use
  to specify the name and/or contact information for the bot owner. This
  information is used when the bot responds to the new `hello` command.
  The default value is `None` in which case no contact information is shared.

Add the following to your `app.cfg` file:

```
ZPARK_CONTACT_INFO = None
```

If you want to specify contact information, add something like the following
to your `app.cfg` file:

```
ZPARK_CONTACT_INFO = "Charlie Root (root@example.com)"
```

Read the [v1.1.0 release notes](relnotes.html#v110).
