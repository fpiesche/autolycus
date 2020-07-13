# Autolycus
<div style="text-align: right; font-size: 1.2em; font-style: italic">Admin tools for the Hercules Ragnarok Online server emulator</div>

Currently, Autolycus is a command-line Python utility that can run and stop your Hercules servers and perform various minor setup and maintenance tasks:

  * Editing (almost) arbitrary configuration files, giving preference to their `import` siblings
  * Setting up database and inter-server configuration for Hercules
  * Creating or editing accounts (for GM rights, say) directly in the database
  * Checking the server status including the database connection

I am planning to expand this into a full web UI to both allow people to sign up for new accounts without having to go through the silly `_M`/`_S` suffix thing and manage the server more generally - a web frontend for restarting the servers, editing accounts/characters, modifying the server configuration, etc.

## Why "Autolycus"? What's that?

I was trying to think of a nicer name for this project than "hercules-admin" and started reading up
on the myth of Hercules. Autolycus was a robber who taught Hercules to wrestle, which is to say,
feasibly the one person in Greece capable of wrestling Hercules.

Also, I like [Bruce Campbell](https://hercules-xena.fandom.com/wiki/Autolycus), so once I stumbled on "Autolycus taught Hercules to wrestle" the decision came easy.

<div align="center">![Bruce Campbell as Autolycus in Xena: Warrior Princess](https://github.com/fpiesche/autolycus/raw/master/autolycus.jpg "Bruce Campbell as Autolycus in Xena: Warrior Princess")</div>
