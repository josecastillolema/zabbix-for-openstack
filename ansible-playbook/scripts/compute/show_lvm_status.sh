e=$(sudo lvs)
if [[ $e ]]; then
   echo 1
else
   echo 0
fi

