
# Sparks `data` commands

Something to ease and empower Django's already excellent `dumpdata` and `loaddata`.
It makes them network and environment aware.

There is no `copydata` command

## Use cases


    # The basics:
    fab test getdata:landing.landingcontents
        test dumpdata …
        get(…)  # named-file, auto-generated with date if not specified
        print(final_filename)

    fab test putdata[:short_filename]
        put(…)  # take latest auto-generated if not found
        test loaddata …


    # test to production via my dev (in 2 operations, just to check):
    fab test copydata:landing.landingcontents,to=local
        test dumpdata …
        get(…)  # transient
        local loaddata …

    fab local copydata:landing.landingcontents,to=production
        local dumpdata …
        put(…) # transient
        production loaddata …


    # from my dev machine to test, with custom settings:
    fab local oneflowapp copydata:landing.landingcontents,to=test[,djsettings=oneflowapp]
    fab local oneflowapp copydata:landing.landingcontents,to='test oneflowapp'
        fab local oneflowapp getdata:landing.landingcontents
        # transient file…
        # prompts for review
        fab test oneflowapp putdata:landing.landingcontents[implicit:,from=transient_file]

    fab test copydata:landing.landingcontents,to=production
        - makes an implicit first test via local?
            - yes, unless ',direct=True'
        - enforces runable? or not? ot just prompts?
