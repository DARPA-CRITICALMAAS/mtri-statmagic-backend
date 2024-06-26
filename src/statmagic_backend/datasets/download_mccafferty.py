from statmagic_backend.extract.sciencebasetools import fetch_sciencebase_files, recursive_download

import logging
logger = logging.getLogger("statmagic_backend")

if __name__ == "__main__":
    
    db_id = "6193e9f3d34eb622f68f13a5"
    write_path = "/home/efvega/data/statmagic"
    
    
    file_registry = fetch_sciencebase_files(db_id, write_path = write_path)
    recursive_download(file_registry, print_only=False)
    
