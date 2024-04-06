"""Query climate data sets by using-key value pair search queries."""

import sys
from functools import cached_property
from typing import Dict, Iterator, List, Literal, Optional, Union, cast
import yaml

import requests
from rich import print as pprint

from .utils import Config, logger

__version__ = "2404.0.0"

__all__ = ["databrowser"]


class databrowser:
    """Find data in the system.

    You can either search for files or uri's. Uri's give you an information
    on the storage system where the files or objects you are looking for are
    located. The query is of the form `key=value`. For `value` you might
    use *, ? Wild cards or any regular expression.

    Parameters
    ~~~~~~~~~~

    **search_keys: str
        The search constraints applied in the data search. If not given
        the whole dataset will be queried.
    flavour: str, default: freva
        The Data Reference Syntax (DRS) standard specifying the type of climate
        datasets to query. You can get an overview by using the
        :py:meth:databrowser.overview class method to retrieve information
        on the available search flavours and their different search keys.
    time: str, default: ""
        Special search key to refine/subset search results by time.
        This can be a string representation of a time range or a single
        timestamp. The timestamps has to follow ISO-8601. Valid strings are
        ``%Y-%m-%dT%H:%M to %Y-%m-%dT%H:%M`` for time ranges or
        ``%Y-%m-%dT%H:%M`` for single time stamps.
        **Note**: You don't have to give the full string format to subset
        time steps: `%Y`, `%Y-%m` etc are also valid.
    time_select: str, default: flexible
        Operator that specifies how the time period is selected. Choose from
        flexible (default), strict or file. ``strict`` returns only those files
        that have the *entire* time period covered. The time search ``2000 to
        2012`` will not select files containing data from 2010 to 2020 with
        the ``strict`` method. ``flexible`` will select those files as
        ``flexible`` returns those files that have either start or end period
        covered. ``file`` will only return files where the entire time
        period is contained within *one single* file.
    uniq_key: str, default: file
        Chose if the solr search query should return paths to files or
        uris, uris will have the file path along with protocol of the storage
        system. Uris can be useful if the search query result should be
        used libraries like fsspec.
    host: str, default: None
        Override the host name of the databrowser server. This is usually the
        url where the freva web site can be found. Such as www.freva.dkrz.de.
        By default no host name is given and the host name will be taken from
        the freva config file.
    multiversion: bool, default: False
        Select all versions and not just the latest version (default).
    fail_on_error: bool, default: False
        Make the call fail if the connection to the databrowser could not
        be established.


    Attributes
    ~~~~~~~~~~

    url: str
        the url of the currently selected databrowser api server
    metadata: dict[str, str]
        The available search keys, or metadata, found for the applied search
        constraints. This can be useful for reverse searches.


    Example
    ~~~~~~~

    Search for the cmorph datasets. Suppose we know that the experiment name
    of this dataset is cmorph therefore we can create in instance of the
    databrowser class using the ``experiment`` search constraint.
    If you just 'print' the created object you will get a quick overview:

    .. execute_code::

        from freva_databrowser import databrowser
        db = databrowser(experiment="cmorph", uniq_key="uri")
        print(db)

    After having created the search object you can aquire differnt kinds of
    information like the number of found objects:

    .. execute_code::

        from freva_databrowser import databrowser
        db = databrowser(experiment="cmorph", uniq_key="uri")
        print(len(db))
        # Get all the search keys associated with this search

    Or you can retrieve the combined metadata of the search objects.

    .. execute_code::

        from freva_databrowser import databrowser
        db = databrowser(experiment="cmorph", uniq_key="uri")
        print(db.metadata)

    Most importantly you can retrieve the locations of all encountered objects

    .. execute_code::

        from freva_databrowser import databrowser
        db = databrowser(experiment="cmorph", uniq_key="uri")
        for file in db:
            pass
        all_files = sorted(db)
        print(all_files[0])


    You can also set a different flavour, for example according to cmip6
    standard:

    .. execute_code::

        from freva_databrowser import databrowser
        db = databrowser(flavour="cmip6", experiment_id="cmorph")
        print(db.metadata)
    """

    def __init__(
        self,
        *,
        uniq_key: Literal["file", "uri"] = "file",
        flavour: Literal[
            "freva", "cmip6", "cmip5", "cordex", "nextgems"
        ] = "freva",
        time: Optional[str] = None,
        host: Optional[str] = None,
        time_select: Literal["flexible", "strict", "file"] = "flexible",
        multiversion: bool = False,
        fail_on_error: bool = False,
        **search_keys: Union[str, List[str]],
    ) -> None:

        self._fail_on_error = fail_on_error
        self._cfg = Config(host, uniq_key=uniq_key, flavour=flavour)
        self._flavour = flavour
        self._params = {**{"multi-version": multiversion}, **search_keys}
        if time:
            self._params["time"] = time
            self._params["time_select"] = time_select

    def __iter__(self) -> Iterator[str]:
        result = self._get(self._cfg.search_url)
        if result is not None:
            try:
                for res in result.iter_lines():
                    yield res.decode("utf-8")
            except KeyboardInterrupt:
                pprint(
                    "[red][b]User interrupt: Exit[/red][/b]", file=sys.stderr
                )

    def __repr__(self) -> str:
        params = ", ".join(
            [f"{k.replace('-', '_')}={v}" for (k, v) in self._params.items()]
        )
        return (
            f"{self.__class__.__name__}(flavour={self._flavour}, "
            f"host={self.url}, {params})"
        )

    def _repr_html_(self) -> str:
        params = ", ".join(
            [f"{k.replace('-', '_')}={v}" for (k, v) in self._params.items()]
        )

        found_objects_count = len(self)

        available_flavours = ", ".join(
            flavour for flavour in self._cfg.overview["flavours"]
        )
        available_search_facets = ", ".join(
            facet for facet in self._cfg.overview["attributes"][self._flavour]
        )

        # Create a table-like structure for available flavors and search facets
        style = 'style="text-align: left"'
        facet_heading = (
            f"Available search facets for <em>{self._flavour}</em> flavour"
        )
        html_repr = (
            "<table>"
            f"<tr><th colspan='2' {style}>{self.__class__.__name__}"
            f"(flavour={self._flavour}, host={self.url}, "
            f"{params})</th></tr>"
            f"<tr><td><b># objects</b></td><td {style}>{found_objects_count}"
            "</td></tr>"
            f"<tr><td valign='top'><b>{facet_heading}</b></td>"
            f"<td {style}>{available_search_facets}</td></tr>"
            "<tr><td valign='top'><b>Available flavours</b></td>"
            f"<td {style}>{available_flavours}</td></tr>"
            "</table>"
        )

        return html_repr

    def __len__(self) -> int:
        """Query the total number of found objects.

        Example
        ~~~~~~~
        .. execute_code::

            from freva_databrowser import databrowser
            print(len(databrowser(experiment="cmorph")))


        """
        result = self._get(self._cfg.metadata_url)
        if result:
            return cast(int, result.json().get("total_count", 0))
        return 0

    @classmethod
    def count_values(
        cls,
        *facets: str,
        flavour: Literal[
            "freva", "cmip6", "cmip5", "cordex", "nextgems"
        ] = "freva",
        time: Optional[str] = None,
        host: Optional[str] = None,
        time_select: Literal["flexible", "strict", "file"] = "flexible",
        multiversion: bool = False,
        fail_on_error: bool = False,
        extendet_search: bool = False,
        **search_keys: Union[str, List[str]],
    ) -> Dict[str, Dict[str, int]]:
        """Count the number of objects in the databrowser.

        Parameters
        ~~~~~~~~~~
        *facets: str
            Count these these facets (attributes & values) instead of the number
            of total files. If None (default), the number of total files will
            be returned.
        flavour: str, default: freva
            The Data Reference Syntax (DRS) standard specifying the type of climate
            datasets to query.
        time: str, default: ""
            Special search facet to refine/subset search results by time.
            This can be a string representation of a time range or a single
            timestamp. The timestamp has to follow ISO-8601. Valid strings are
            ``%Y-%m-%dT%H:%M`` to ``%Y-%m-%dT%H:%M`` for time ranges and
            ``%Y-%m-%dT%H:%M``. **Note**: You don't have to give the full string
            format to subset time steps ``%Y``, ``%Y-%m`` etc are also valid.
        time_select: str, default: flexible
            Operator that specifies how the time period is selected. Choose from
            flexible (default), strict or file. ``strict`` returns only those files
            that have the *entire* time period covered. The time search ``2000 to
            2012`` will not select files containing data from 2010 to 2020 with
            the ``strict`` method. ``flexible`` will select those files as
            ``flexible`` returns those files that have either start or end period
            covered. ``file`` will only return files where the entire time
            period is contained within *one single* file.
        extendet_search: bool, default: False
            Retrieve information on additional search keys.
        host: str, default: None
            Override the host name of the databrowser server. This is usually
            the url where the freva web site can be found. Such as
            www.freva.dkrz.de. By default no host name is given and the host
            name will be taken from the freva config file.
        multiversion: bool, default: False
            Select all versions and not just the latest version (default).
        fail_on_error: bool, default: False
            Make the call fail if the connection to the databrowser could not
        **search_keys: str
            The search contraints to be applied in the data search. If not given
            the whole dataset will be queried.

        Returns
        ~~~~~~~
        dict[str, int]:
            Dictionary with the number of objects for each search facet/key
            is given.

        Example
        ~~~~~~~

        .. execute_code::

            from freva_databrowser import databrowser
            print(databrowser.count_values(experiment="cmorph"))

        .. execute_code::

            from freva_databrowser import databrowser
            print(databrowser.count_values("model"))

        """
        this = cls(
            flavour=flavour,
            time=time,
            time_select=time_select,
            host=host,
            multiversion=multiversion,
            fail_on_error=fail_on_error,
            uniq_key="file",
            **search_keys,
        )
        result = this._facet_search(*facets, extendet_search=extendet_search)
        counts = {}
        for facet, value_counts in result.items():
            counts[facet] = dict(
                zip(value_counts[::2], map(int, value_counts[1::2]))
            )
        return counts

    @cached_property
    def metadata(self) -> Dict[str, List[str]]:
        """Get the metadata (facets) for the current databrowser query.

        You can retrieve all information that is associated with your current
        databrowser search. This can be useful for reverse searches for example
        for retrieving metadata of object sotres or file/directory names.

        Example
        ~~~~~~~

        Reverse search: retrieving meta data from a known file

        .. execute_code::

            from freva_databrowser import databrowser
            db = databrowser(uri="slk:///arch/*/CPC/*")
            print(db.metadata)


        """
        return {
            k: v[::2]
            for (k, v) in self._facet_search(extendet_search=True).items()
        }

    @classmethod
    def metadata_search(
        cls,
        *facets: str,
        flavour: Literal[
            "freva", "cmip6", "cmip5", "cordex", "nextgems"
        ] = "freva",
        time: Optional[str] = None,
        host: Optional[str] = None,
        time_select: Literal["flexible", "strict", "file"] = "flexible",
        multiversion: bool = False,
        fail_on_error: bool = False,
        extendet_search: bool = False,
        **search_keys: Union[str, List[str]],
    ) -> Dict[str, List[str]]:
        """Search for data attributes (facets) in the databrowser.

        The method queries the databrowser for available search facets (keys)
        like model, experiment etc.

        Parameters
        ~~~~~~~~~~

        *facets: str,
            Get only information on these selected search keys (facets). By
            default information on all available facets is retrieved.
        flavour: str, default: freva
            The Data Reference Syntax (DRS) standard specifying the type of climate
            datasets to query.
        time: str, defautl: ""
            Special search facet to refine/subset search results by time.
            This can be a string representation of a time range or a single
            timestamp. The timestamp has to follow ISO-8601. Valid strings are
            ``%Y-%m-%dT%H:%M`` to ``%Y-%m-%dT%H:%M`` for time ranges and
            ``%Y-%m-%dT%H:%M``. **Note**: You don't have to give the full string
            format to subset time steps ``%Y``, ``%Y-%m`` etc are also valid.
        time_select: str, default: flexible
            Operator that specifies how the time period is selected. Choose from
            flexible (default), strict or file. ``strict`` returns only those files
            that have the *entire* time period covered. The time search ``2000 to
            2012`` will not select files containing data from 2010 to 2020 with
            the ``strict`` method. ``flexible`` will select those files as
            ``flexible`` returns those files that have either start or end period
            covered. ``file`` will only return files where the entire time
            period is contained within *one single* file.
        extendet_search: bool, default: False
            Retrieve information on additional search keys.
        multiversion: bool, default: False
            Select all versions and not just the latest version (default).
        host: str, default: None
            Override the host name of the databrowser server. This is usually
            the url where the freva web site can be found. Such as
            www.freva.dkrz.de. By default no host name is given and the host
            name will be taken from the freva config file.
        fail_on_error: bool, default: False
            Make the call fail if the connection to the databrowser could not
        **search_keys: str, list[str]
            The facets to be applied in the data search. If not given
            the whole dataset will be queried.

        Returns
        ~~~~~~~
        dict[str, list[str]]:
            Dictionary with a list search facet values for each search facet key


        Example
        ~~~~~~~

        .. execute_code::

            from freva_databrowser import databrowser
            all_facets = databrowser.metadata_search(project='obs*')
            print(all_facets)

        You can also search for all metadata matching a search string:

        .. execute_code::

            from freva_databrowser import databrowser
            spec_facets = databrowser.metadata_search("obs*")
            print(spec_facets)

        Get all models that have a given time step:

        .. execute_code::

            from freva_databrowser import databrowser
            model = databrowser.metadata_search(
                project="obs*",
                time="2016-09-02T22:10"
            )
            print(model)

        Reverse search: retrieving meta data from a known file

        .. execute_code::

            from freva_databrowser import databrowser
            res = databrowser.metadata_search(file="/arch/*CPC/*")
            print(res)

        """
        this = cls(
            flavour=flavour,
            time=time,
            time_select=time_select,
            host=host,
            multiversion=multiversion,
            fail_on_error=fail_on_error,
            uniq_key="file",
            **search_keys,
        )
        return {
            k: v[::2]
            for (k, v) in this._facet_search(
                *facets, extendet_search=extendet_search
            ).items()
        }

    @classmethod
    def overview(cls, host: Optional[str] = None) -> str:
        """Get an overview over the available search options.

        If you don't know what search flavours or search keys you can use
        for searching the data you can use this method to get an overview
        over what is available.

        Parameters
        ~~~~~~~~~~

        host: str, default None
            Override the host name of the databrowser server. This is usually
            the url where the freva web site can be found. Such as
            www.freva.dkrz.de. By default no host name is given and the host
            name will be taken from the freva config file.

        Returns
        ~~~~~~~
        str: A string representation over what is available.

        Example
        ~~~~~~~

        :: execute_code::

            from freva_client import databrowser
            print(databrowser.overview())
        """
        overview = Config(host).overview.copy()
        overview["Available search flavours"] = overview.pop("flavours")
        overview["Search attributes by flavour"] = overview.pop("attributes")
        return yaml.safe_dump(overview)

    @property
    def url(self) -> str:
        """Get the url of the databrowser API."""
        return self._cfg.databrowser_url

    def _facet_search(
        self,
        *facets: str,
        extendet_search: bool = False,
    ) -> Dict[str, List[str]]:
        result = self._get(self._cfg.metadata_url)
        if result is None:
            return {}
        data = result.json()
        contraints = [f for f in facets if f != "*"]
        if extendet_search:
            contraints = contraints or data["facets"].keys()
        else:
            contraints = contraints or data["primary_facets"]
        return {f: v for f, v in data["facets"].items() if f in contraints}

    def _get(self, url: str) -> Optional[requests.models.Response]:
        """Apply the get method to the databrowser."""
        logger.debug("Searching %s with parameters: %s", url, self._params)
        try:
            res = requests.get(url, params=self._params, timeout=30)
            res.raise_for_status()
            return res
        except KeyboardInterrupt:
            pprint("[red][b]User interrupt: Exit[/red][/b]", file=sys.stderr)
        except (
            requests.exceptions.ConnectionError,
            requests.exceptions.HTTPError,
        ) as error:
            msg = f"Search request failed with {error}"
            if self._fail_on_error:
                raise ValueError(msg) from None
            logger.warning(msg)
        return None
