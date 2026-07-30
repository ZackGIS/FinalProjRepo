using Newtonsoft.Json.Linq;
using TMPro;
using Unity.Hierarchy;
using Unity.VisualScripting;
using UnityEditor.ShaderGraph.Internal;
using UnityEngine;
using UnityEngine.UI;
using System.Collections.Generic;

public class PopupManager : MonoBehaviour
{
    [SerializeField]
    private GameObject popup;

    [SerializeField]
    private TMP_Text popupTitle;

    //[SerializeField]
    //private TMP_Text popupBody;

    [SerializeField]
    private Button closeButton;

    [SerializeField]
    private Transform propertyContainer;

    [SerializeField]
    private PropertyRow propertyRowPrefab;

    private List<PropertyRow> propertyRows = new List<PropertyRow>();   

    //public Camera mainCamera;

    private void Awake()
    {
        popup.SetActive(false);
        closeButton.onClick.AddListener(ClosePopup);
    }

    private void ClosePopup()
    {  
        ClearProperties();  
    }

    private void ClearProperties()
    {
        foreach (PropertyRow row in propertyRows)
        {
            if (row != null)
            {
                Destroy(row.gameObject);
            }
        }

        propertyRows.Clear();
        popup.SetActive(false);
    }

    private void CreatePropertyRow(string name, string value)
    {
        PropertyRow row = Instantiate(propertyRowPrefab, propertyContainer);
        propertyRows.Add(row);
        row.Initialize(name, value);
    }

    public void Show(FeatureInfo feature)
    {
        ClearProperties();
        popup.SetActive(true);
        popupTitle.text = feature.GeometryType;

        foreach (var coordinate in feature.GetCoordinates())
        {
            CreatePropertyRow("Coordinates", (coordinate.latitude, coordinate.longitude).ToString());
        }

        foreach (JProperty property in feature.GetAllProperties())
        {
            CreatePropertyRow(property.Name, property.Value.ToString());
        }

    }


}
