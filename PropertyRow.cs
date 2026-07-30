using UnityEngine;
using TMPro;

public class PropertyRow : MonoBehaviour
{
    [SerializeField] 
    private TMP_Text propertName;
    
    [SerializeField] 
    private TMP_Text porpertyValue;

    public void Initialize(string name, string value)
    {
        propertName.text = name;
        porpertyValue.text = value; 
    }
}
