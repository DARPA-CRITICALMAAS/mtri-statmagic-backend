import httpx
import json
import os
import pandas as pd
import io

class CDR():
    '''
    Class with utils for interfacing with the CDR

    '''

    def __init__ (
            self,
            cdr_host = "https://api.cdr.land",
            cdr_version = 'v1'
        ):
        '''
        On initialization, register authentication headers and httpx client

        Parameters
        ----------
        cdr_host : str
                   URL of the CDR API server


        '''

        self.cdr_host = cdr_host
        self.cdr_version = cdr_version

        token = os.environ['CDR_API_TOKEN']

        self.headers = {"Authorization": f"Bearer {token}"}
        self.client = httpx.Client(follow_redirects=True)

        # Set an extended timeout period b/c the CSV endpoints in particular
        # take longer than the default of 5 seconds
        self.timeout_seconds = 60


    def process_csv_result(self,content_bytes):
        '''
        Processes a CSV return from CDR endpoint; expects "content_bytes"

        Parameters
        ----------
        content_bytes bytes
            Return from httpx "content" call to CDR API endpoint that return as
            CSV

        Returns
        -------
        response : pandas dataframe
            Represents CSV response from API
        '''
        return pd.read_csv(io.BytesIO(content_bytes))


    def run_query(self,query,csv=False):
        '''
        Queries a CDR API endpoint

        Parameters
        ----------
        query : str
            URL representing API endpoint including args, not including API
            server host name/version, e.g.
                'knowledge/csv/mineral_site_grade_and_tonnage/copper'

        csv : bool
            Indicates whether or not response is a CSV; if not assumed to be
            JSON

        Returns
        -------
        response : dict OR pandas data frame
            API response which is either dict representing JSON or if csv=True,
            a pandas data frame representing CSV response
        '''
        resp = self.client.get(
            f'{self.cdr_host}/{self.cdr_version}/{query}',
            headers=self.headers,
            timeout=self.timeout_seconds
        )

        # If not a CSV response, assume JSON
        if csv:
            data = self.process_csv_result(resp.content)
        else:
            data = resp.json()

        return data

    def get_deposit_types(self):
        return self.run_query('knowledge/deposit_types')

    def get_commodity_list(self):
        return self.run_query('knowledge/commodities')


    def get_mineral_site_grade_and_tonnage(self,commodity):
        '''

        Parameters
        ----------
        commodity : str
            name of commodity, e.g. 'copper'

        Returns
        -------
        response : pandas dataframe
            represents CSV results from API
        '''

        return self.run_query(
            f'knowledge/csv/mineral_site_grade_and_tonnage/{commodity}',
            csv=True
        )

    def get_mineral_site_deposit_type_classification_results(self,commodity):
       return self.run_query(
           f'knowledge/csv/mineral_site_deposit_type_classificiation_results/{commodity}',
           csv=True
       )

    def get_hyper_site_results(self,commodity):
        return self.run_query(
            f'knowledge/csv/hyper_site_results/{commodity}',
            csv=True
        )

    def get_mineral_site_inventories(self,commodity):
        return self.run_query(
            f'knowledge/csv/mineral_site_inventories/{commodity}',
            csv=True
        )

    def get_mineral_site_deposit_type_candidates(self,deposit_type_name):
        '''

        Parameters
        ----------
        deposit_type_name : str
            deposit type name (see list of opts from get_deposit_types()), e.g.:
            "Epithermal mercury"

        Returns
        -------
        response : pandas dataframe
            represents CSV results from API
        '''
        return self.run_query(
            f'knowledge/mineral_site_deposit_type_candidates/{deposit_type_name}'
        )

    def get_mineral_site_deposit_type_candidates_csv(self, deposit_type_name):
        '''
        Parameters
        ----------
        deposit_type_name : str
            deposit type name (see list of opts from get_deposit_types()), e.g.:
            "Epithermal mercury"

        Returns
        -------
        response : dict
            dict representing JSON response from API
        '''
        return self.run_query(
            f'knowledge/csv/mineral_site_deposit_type_candidates/{deposit_type_name}',
            csv=True
        )



### Testing code...
#cdr = CDR()
#print(cdr.get_deposit_types())
#print(cdr.get_commodity_list())
#print(cdr.get_mineral_site_grade_and_tonnage('copper'))
#print(cdr.get_mineral_site_deposit_type_classification_results('copper'))

#print(cdr.get_hyper_site_results('copper'))
#print(cdr.get_mineral_site_inventories('copper')) # <- this one always times out

#print(cdr.get_mineral_site_deposit_type_candidates('Epithermal mercury'))
#print(cdr.get_mineral_site_deposit_type_candidates_csv('Epithermal mercury'))

