# digital-advisor

Digital Advisor's project management command.

An example session might look like the following:

    $ da create example.com
    $ da setup
    $ da add news
    $ da run
    $ da test
    $ da stage
    $ da launch

This will, in order:

1. Copy a skeleton project, including websever settings, substituting domain names
   as needed, and creating a repo on our private git server.
2. Create a Python virtual environment and install any necessary libraries.
3. Add a bare-bones *news* app ready for customisation.
4. Run a local web server for development purposes.
5. Run the project's unit and integration tests.
6. Deploy the project to the staging server (after running tests,
   migrating DB, etc.)
7. As above, but to the production server.


## Wrapper script

The Python program is named `digital_advisor`, but the bash script `da` is the
usual entry point. If all goes well, it will simply run the Python project,
passing along any command-line arguments.

If a required library is missing the Python package will use error code `100`
to commmunicate that fact and the wrapper script will create a new Python
virtual environment, then install into it the required libraries.
