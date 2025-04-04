using UnityEngine;
using System.IO;
using Esri.GameEngine.Geometry;
using Esri.ArcGISMapsSDK.Components;
using Newtonsoft.Json.Linq;
using System.Collections;
using Esri.HPFramework;

public class GeoJSONLoader : MonoBehaviour
{
    public string geoJSONFilePath = @"C:\Users\theim\PycharmProjects\pythonProject4\locations.geojson"; //file path for geojson
    public GameObject pointPrefab;   //declaring GameObject variable. Each feature in the geojson file will be created

    private float defaultAltitude = 1000.0f; // Default is set to 1000ft. Want to ensure the features are visible for testing.
    public ArcGISMapComponent map;          //ArcGISMpaComponent object

    void Start()
    {
        GameObject mapGameObject = GameObject.Find("ArcGISMap");

        if (mapGameObject != null)
        {
            map = mapGameObject.GetComponent<ArcGISMapComponent>();

            if (map != null)
            {
                Debug.Log("ArcGISMapComponent successfully assigned.");
                StartCoroutine(WaitForMapInitialization());
            }
            else
            {
                Debug.LogError("ArcGISMapComponent not found on the GameObject.");
            }
        }
        else
        {
            Debug.LogError("GameObject 'ArcGISMap' not found in the scene.");
        }
    }

    //Funtion to make sure the map is active in the game object hierarchy before doing anything else. Once this is confirmed
    //LoadGeoJSON() is called
    IEnumerator WaitForMapInitialization()
    {
        while (!map.gameObject.activeInHierarchy)
        {
            Debug.Log("Waiting for ArcGISMapComponent to activate...");
            yield return null; // Wait for the next frame
        }

        Debug.Log("ArcGISMapComponent is active.");
        LoadGeoJSON();
    }

    // Function below to load the geojson and parse its geospatial data
    private void LoadGeoJSON()
    {
        string geoJSONText = File.ReadAllText(geoJSONFilePath); //create an object to read text from the input file path defined in variables section.
        JObject geoJSONData = JObject.Parse(geoJSONText); //JObject and the Parse() fucntion are from the Newtonsoft Json library. in this case I'm parsing the 
                                                           // text from the file path and storing that in a JObject called geoJSONData

        foreach (var feature in geoJSONData["features"])  //loop through all of the features in geoJSONData
        {
            var coordinates = feature["geometry"]["coordinates"]; //coordinates are nested within the "geometry" attribute
            double lat = (double)coordinates[0];                    //cast lat and lon as a double
            double lon = (double)coordinates[1];

            PlaceMarker(lat, lon); //create the game object map feature at the coordinates.
        }

        //right now I'm only parsing the geospatial data but this has to be extended to all of the attribute data contained for each feature.
    }

    // Function to create the game object the the heiracrchy procedurally. Takes the lat, lon coordinates as parameters. 
    private void PlaceMarker(double latitude, double longitude)
    {
        GameObject marker = pointPrefab ? Instantiate(pointPrefab) : GameObject.CreatePrimitive(PrimitiveType.Sphere); // For now I'm just creating simple spheres but this will
                                                                                                                        //change later
        marker.transform.localScale = Vector3.one * 500.0f; // Scale of spheres needs to be increased dramatically so they are visisble on the map.

        // Add the marker to the map GameObject immediately to prevent parenting errors later
        marker.transform.SetParent(map.transform, true); // true to retain world position

        // Delay initialization of the ArcGISLocationComponent (have to wait until the game objects are loaded for each geojson feature)
        StartCoroutine(InitializeMarkerLocation(marker, latitude, longitude));
        Debug.Log($"Marker created for latitude: {latitude}, longitude: {longitude}, waiting for initialization."); // Keep this Debug.Log for now
    }

    private IEnumerator InitializeMarkerLocation(GameObject marker, double latitude, double longitude)
    {
        while (!map.gameObject.activeInHierarchy)
        {
            Debug.Log("Waiting for ArcGISMapComponent to become active...");
            yield return null; // Wait for the next frame
        }

        var locationComponent = marker.AddComponent<ArcGISLocationComponent>();
        locationComponent.Position = new ArcGISPoint(longitude, latitude, defaultAltitude, ArcGISSpatialReference.WGS84());

        Debug.Log($"Marker initialized at latitude: {latitude}, longitude: {longitude}, altitude: {defaultAltitude}");
    }
}
