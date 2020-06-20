# How to contribute

## Submitting changes

Please send a [GitHub Pull Request](https://github.com/josecastillolema/zabbix-for-openstack/pull/new/master) with a clear list of what has been done (read more about [pull requests](http://help.github.com/pull-requests/)). Please follow coding conventions (below) and make sure all of the commits are atomic (one feature per commit).

Always write a clear log message for the commits. One-line messages are fine for small changes, but bigger changes should look like this:

    $ git commit -m "A brief summary of the commit
    > 
    > A paragraph describing what changed and its impact."
    
### Preparing the Fork

1. Click 'Fork' on Github, creating e.g. ``username/theproject``.
2. Clone the project: ``git clone git@github.com:username/theproject``.
3. Create a branch: ``git checkout -b foo-the-bars 1.3``.

### Making the Changes

1. Add changelog entry.
2. Write your changes.
3. Commit your changes: ``git commit -m "Foo the bars"``

### Creating Pull Requests

1. Push the commit to get it back up to your fork: ``git push origin HEAD``
2. Visit Github, click "Pull request" button that it will make upon
   noticing your new branch.
3. In the description field, write down issue number (if submitting code fixing
   an existing issue) or describe the issue + your fix (if submitting a wholly
   new bugfix).
4. Hit 'submit'.

## Coding conventions

  * **Follow the style you see used in the primary repository**. Consistency with
  the rest of the project always trumps other considerations.
  * The code is indented using four spaces (soft tabs).
  * This is open source software. Consider the people who will read the code.
