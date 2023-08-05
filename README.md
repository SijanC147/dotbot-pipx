Dotbot-ruby
=============

Plugin for [dotbot](https://github.com/anishathalye/dotbot) that knows
how to install ruby gems.

Usage
-----

Add this repo as subrepo to your dotfiles and update `install` script.

```bash
git submodule add https://github.com/sijanc147/dotbot-ruby
```

Then, modify install script to add path to `dotbot-ruby` directory that you
just added. Only last line is relevant (if it was not changed from default) and
after change it might look like this:

```bash
"${BASEDIR}/${DOTBOT_DIR}/${DOTBOT_BIN}" -d "${BASEDIR}" -c "${CONFIG}" --plugin-dir=dotbot-ruby "${@}"
```

To use it, add go directive. Values can be simple (only package name) or more
detailed (dict with flags passed to `gem install` command). Example:

```yaml
- ruby:
  - iStats
  - gem: chronic
    flags: ['--user-install']
    stdout: true
    stderr: true
```

