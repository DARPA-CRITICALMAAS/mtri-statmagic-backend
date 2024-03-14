import time
from pathlib import Path

import pooch
import sciencebasepy

sleep_time = 1.0


def create_sciencebase_registry(item_json):
    """
    Creates dictionaries mapping filenames to hashes and URLs

    Parameters
    ----------
    item_json : dict
        Dictionary containing a list of filenames under the key ``'files'``

    Returns
    -------
    registry_dict : dict
        Dictionary mapping filenames to hashes
    urls_dict : dict
        Dictionary mapping filenames to URLs

    """
    # Get names, hashes, and URLS
    list_of_files = item_json['files']

    names = list(map(lambda f: f['name'], list_of_files))
    hashes = list(map(lambda f: f['checksum']['type'] + ':' + f['checksum']['value'], list_of_files))
    urls = list(map(lambda f: f['downloadUri'], list_of_files))

    registry_dict = {name: h for (name, h) in zip(names, hashes)}
    urls_dict = {name: url for (name, url) in zip(names, urls)}

    return registry_dict, urls_dict

def fetch_sciencebase_files(id, sciencebase_session = None, write_path=None):
    """
    Recursively fetches the file hashes from sciencebase.org and stores them
    in the ``pooch`` registry.

    Parameters
    ----------
    id : str
        The ID of the item to fetch from ScienceBase
    sciencebase_session : sciencebasepy.SbSession, optional
        ScienceBase session object (only used inside recursive calls)
    write_path : str
        Path to store ``pooch`` registry.

    Returns
    -------
    puppy_dict : dict
        Dictionary containing ``pooch`` objects, to be parsed by
        :func:`recursive_download`

    """
    if sciencebase_session is None:
        sciencebase_session = sciencebasepy.SbSession()
        time.sleep(sleep_time)

    puppy_dict = {}

    if isinstance(id, str):

        print(f"Sleeping for {sleep_time} seconds")
        time.sleep(sleep_time)
        # create registry
        item_json = sciencebase_session.get_item(id)
    else:
        item_json = id

    if write_path is None:
        write_path = pooch.os_cache(item_json["title"])

    registry, urls = create_sciencebase_registry(item_json)

    puppies = []
    if item_json['hasChildren']:
        print(f"Sleeping for {sleep_time} seconds")
        time.sleep(sleep_time)

        childIds = sciencebase_session.get_child_ids(id)
        for childId in childIds:
            print(f"Sleeping for {sleep_time} seconds")
            time.sleep(sleep_time)
            childItem = sciencebase_session.get_item(childId)
            childWritePath = write_path / Path(childItem["title"])
            puppy = fetch_sciencebase_files(childItem, sciencebase_session, write_path = childWritePath)
            puppies.append(puppy)
    puppy_dict["puppies"] = puppies

    # fetch with pooch
    trained_pooch = pooch.create(
        path=write_path,
        base_url="",
        registry = registry,
        urls = urls
    )

    puppy_dict["pooch"] = trained_pooch
    puppy_dict["item_json"] = item_json

    # return list of filenames
    return puppy_dict


def recursive_download(pooch_tree, print_only = False):
    """
    Recursively downloads the actual files from sciencebase.org if they aren't
    already cached in the pooch registry

    Parameters
    ----------
    pooch_tree : dict
        Output of :func:`fetch_sciencebase_files`
    print_only : bool, optional
        If ``True``, dry run (just print paths without downloading anything).

    Notes
    -----
    No return value. Writes directly to disk.

    """
    pooch_colletion = pooch_tree["pooch"]
    items = []
    for item in pooch_colletion.registry:
        if print_only:
            # print(item + '->' + str(pooch_colletion.path))
            print(item)
            items.append(item)
        else:
            print(f"Sleeping for {sleep_time} seconds")
            time.sleep(sleep_time)
            pooch_colletion.fetch(item)
    for puppy in pooch_tree["puppies"]:
        items = items + recursive_download(puppy, print_only=print_only)

    return items
