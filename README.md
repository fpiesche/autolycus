# Autolycus
<p align="right"><i>Admin tools for the Hercules Ragnarok Online server emulator</i></div>

Currently, Autolycus is a command-line Python utility that can run and stop your Hercules servers
and perform various minor setup and maintenance tasks:

  * Editing (almost) arbitrary configuration files, giving preference to their `import` siblings
  * Setting up database and inter-server configuration for Hercules
  * Creating or editing accounts (for GM rights, say) directly in the database
  * Checking the server status including the database connection

I am planning to expand this into a full web UI to both allow people to sign up for new accounts
without having to go through the silly `_M`/`_S` suffix thing and manage the server more generally -
a web frontend for restarting the servers, editing accounts/characters, modifying the server
configuration, etc.

## How do I use this?

There's a whole bunch of functionality already. Best way to find out what Autolycus can do is to run
`autolycus.py --help`. Here's what that'll tell you:

    usage: autolycus.py [-h] [-p HERCULES_PATH] [-r]
                        {info,start,stop,restart,sql_upgrades,setup_all,setup_db,setup_interserver,account,import_sql}
                        ...

    optional arguments:
      -h, --help            show this help message and exit
      -p HERCULES_PATH, --hercules_path HERCULES_PATH
                            The path containing the Hercules installation to
                            control. (default: .)
      -r, --autorestart     Automatically restart servers when making
                            configuration changes. (default: False)

    Available commands:
      {info,start,stop,restart,sql_upgrades,setup_all,setup_db,setup_interserver,account,import_sql}
        info                Output server status and version information and exit.
        start               Start the game servers.
        stop                Stop the game servers.
        restart             Stop and restart the game servers.
        sql_upgrades        Run any SQL upgrades needed.
        setup_all           Set up database and inter-server config and run SQL
                            upgrades.
        setup_db            Set up the database server configuration.
        setup_interserver   Set up the inter-server communications configuration.
        account             Edit or create an account on the server.
        import_sql          Import an SQL file into the database.

To get more help for any of the commands, run: `autolycus.py [command] --help`

## Why "Autolycus"? What's that?

I was trying to think of a nicer name for this project than "hercules-admin" and started reading up
on the myth of Hercules. Autolycus was a robber who taught Hercules to wrestle, which is to say,
feasibly the one person in Greece capable of wrestling Hercules.

Also, I like [Bruce Campbell](https://hercules-xena.fandom.com/wiki/Autolycus), so once I stumbled on "Autolycus taught Hercules to wrestle" the decision came easy.
<p align="center">
<img src="https://github.com/fpiesche/autolycus/raw/master/autolycus.jpg" alt="Bruce Campbell as Autolycus in Xena: Warrior Princess" />
</p>
